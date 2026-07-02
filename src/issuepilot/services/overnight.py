from __future__ import annotations

import logging
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from issuepilot.config import Settings
from issuepilot.domain import Candidate, Ranking
from issuepilot.models import IssueRecord
from issuepilot.schemas import OvernightResult
from issuepilot.services.bundles import BundleService
from issuepilot.services.github import GitHubScanner
from issuepilot.services.ranking import RankingService
from issuepilot.services.repository import RepositoryService

logger = logging.getLogger(__name__)


class OvernightService:
    def __init__(
        self,
        settings: Settings,
        scanner: GitHubScanner | None = None,
        ranking: RankingService | None = None,
        repositories: RepositoryService | None = None,
        bundles: BundleService | None = None,
    ) -> None:
        self.settings = settings
        self.scanner = scanner or GitHubScanner(settings)
        self.ranking = ranking or RankingService()
        self.repositories = repositories or RepositoryService()
        self.bundles = bundles or BundleService()

    def run(self, session: Session) -> OvernightResult:
        candidates = self.scanner.discover()
        ranked = sorted(
            ((candidate, self.ranking.rank(candidate)) for candidate in candidates),
            key=lambda item: item[1].score,
            reverse=True,
        )[: self.settings.max_issues]
        prepared_ids: list[int] = []
        failed = 0
        for candidate, ranking in ranked:
            try:
                record = self._upsert(session, candidate, ranking)
                session.commit()
                repository_path = self.repositories.clone_or_update(
                    candidate.clone_url, candidate.repository, self.settings.workspace_dir
                )
                metadata = self.repositories.analyze(repository_path)
                record.repo_path = str(repository_path)
                record.repository_metadata = metadata
                record.has_tests = bool(metadata.get("test_framework")) or candidate.has_tests
                record.has_ci = bool(metadata.get("ci")) or candidate.has_ci
                bundle = self.bundles.generate(record, repository_path, self.settings.tasks_dir)
                record.bundle_path = str(bundle)
                session.commit()
                prepared_ids.append(record.id)
                logger.info("Prepared issue %s#%d", candidate.repository, candidate.number)
            except Exception:
                session.rollback()
                failed += 1
                logger.exception("Failed to prepare %s#%d", candidate.repository, candidate.number)
        return OvernightResult(
            discovered=len(candidates),
            prepared=len(prepared_ids),
            failed=failed,
            issue_ids=prepared_ids,
        )

    @staticmethod
    def _upsert(session: Session, candidate: Candidate, ranking: Ranking) -> IssueRecord:
        record = session.scalar(
            select(IssueRecord).where(IssueRecord.github_id == candidate.github_id)
        )
        if record is None:
            record = IssueRecord(
                github_id=candidate.github_id,
                number=candidate.number,
                repository=candidate.repository,
                repository_url=candidate.repository_url,
                clone_url=candidate.clone_url,
                title=candidate.title,
                body=candidate.body,
                issue_url=candidate.issue_url,
                issue_created_at=candidate.issue_created_at,
            )
            session.add(record)
        candidate_data = asdict(candidate)
        for field in (
            "number", "repository", "repository_url", "clone_url", "title", "body",
            "issue_url", "labels", "stars", "comments", "issue_created_at", "repo_pushed_at",
            "has_tests", "has_ci",
        ):
            setattr(record, field, candidate_data[field])
        record.score = ranking.score
        record.difficulty = ranking.difficulty
        record.estimated_minutes = ranking.estimated_minutes
        record.acceptance_probability = ranking.acceptance_probability
        record.ranking_factors = ranking.factors
        return record

