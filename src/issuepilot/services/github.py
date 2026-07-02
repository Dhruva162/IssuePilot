from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from github import Auth, Github
from github.GithubException import GithubException, RateLimitExceededException

from issuepilot.config import Settings
from issuepilot.domain import Candidate

logger = logging.getLogger(__name__)


class GitHubScanner:
    def __init__(self, settings: Settings) -> None:
        auth = Auth.Token(settings.github_token) if settings.github_token else None
        self.client = Github(auth=auth, timeout=30, retry=2)
        self.settings = settings

    def discover(self) -> list[Candidate]:
        logger.info("Searching GitHub with query: %s", self.settings.github_query)
        candidates: list[Candidate] = []
        seen_repositories: set[str] = set()
        try:
            issues = self.client.search_issues(
                query=self.settings.github_query, sort="updated", order="desc"
            )
            for issue in issues:
                if len(candidates) >= self.settings.max_issues * 3:
                    break
                repository = issue.repository
                if repository.full_name in seen_repositories:
                    continue
                if not self._eligible(repository):
                    continue
                seen_repositories.add(repository.full_name)
                candidates.append(self._candidate(issue, repository))
        except RateLimitExceededException as exc:
            raise RuntimeError(
                "GitHub rate limit exceeded. Set GITHUB_TOKEN in .env and retry."
            ) from exc
        except GithubException as exc:
            raise RuntimeError(f"GitHub search failed: {exc.data}") from exc
        logger.info("Discovered %d eligible issues", len(candidates))
        return candidates

    def _eligible(self, repository: Any) -> bool:
        return (
            not repository.archived
            and not repository.fork
            and repository.stargazers_count >= self.settings.min_stars
            and repository.size <= self.settings.max_repo_size_kb
            and repository.has_issues
        )

    def _candidate(self, issue: Any, repository: Any) -> Candidate:
        contents = self._root_names(repository)
        maintainer_activity = self._maintainer_activity(repository)
        return Candidate(
            github_id=issue.id,
            number=issue.number,
            repository=repository.full_name,
            repository_url=repository.html_url,
            clone_url=repository.clone_url,
            title=issue.title,
            body=issue.body or "",
            issue_url=issue.html_url,
            labels=[label.name for label in issue.labels],
            stars=repository.stargazers_count,
            comments=issue.comments,
            issue_created_at=self._aware(issue.created_at),
            repo_pushed_at=self._aware(repository.pushed_at) if repository.pushed_at else None,
            maintainer_activity=maintainer_activity,
            has_tests=any(name in contents for name in {"test", "tests", "spec", "pytest.ini"}),
            has_ci=".github" in contents or ".gitlab-ci.yml" in contents,
            repo_size_kb=repository.size,
        )

    def _root_names(self, repository: Any) -> set[str]:
        try:
            return {item.name.lower() for item in repository.get_contents("")}
        except GithubException:
            return set()

    def _maintainer_activity(self, repository: Any) -> float:
        since = datetime.now(UTC) - timedelta(days=90)
        try:
            recent = repository.get_commits(since=since).totalCount
            return min(100.0, recent * 5.0)
        except GithubException:
            return 0.0

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)

