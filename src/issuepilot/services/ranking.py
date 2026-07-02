from __future__ import annotations

import math
from datetime import UTC, datetime

from issuepilot.domain import Candidate, Ranking


class RankingService:
    """Transparent deterministic ranking; every component is persisted for inspection."""

    def rank(self, candidate: Candidate, now: datetime | None = None) -> Ranking:
        now = now or datetime.now(UTC)
        issue_age = max(0, (now - self._aware(candidate.issue_created_at)).days)
        push_age = (
            max(0, (now - self._aware(candidate.repo_pushed_at)).days)
            if candidate.repo_pushed_at
            else 365
        )

        factors = {
            "stars": min(100.0, math.log10(candidate.stars + 1) / 5 * 100),
            "recent_commits": max(0.0, 100 - push_age * 2.5),
            "maintainer_activity": max(0.0, min(100.0, candidate.maintainer_activity)),
            "tests": 100.0 if candidate.has_tests else 15.0,
            "ci": 100.0 if candidate.has_ci else 20.0,
            "issue_age": self._age_score(issue_age),
            "comments": self._comments_score(candidate.comments),
        }
        weights = {
            "stars": 0.14,
            "recent_commits": 0.20,
            "maintainer_activity": 0.20,
            "tests": 0.14,
            "ci": 0.10,
            "issue_age": 0.12,
            "comments": 0.10,
        }
        score = round(sum(factors[key] * weights[key] for key in factors), 1)
        difficulty, minutes = self._difficulty(candidate)
        acceptance = round(
            min(
                0.95,
                max(
                    0.15,
                    0.30
                    + factors["maintainer_activity"] * 0.0025
                    + factors["recent_commits"] * 0.0015
                    + factors["tests"] * 0.001
                    - min(candidate.comments, 20) * 0.005,
                ),
            ),
            2,
        )
        return Ranking(score, difficulty, minutes, acceptance, factors)

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    @staticmethod
    def _age_score(days: int) -> float:
        if days < 3:
            return 45.0
        if days <= 90:
            return 100.0
        return max(20.0, 100 - (days - 90) * 0.2)

    @staticmethod
    def _comments_score(comments: int) -> float:
        if comments == 0:
            return 65.0
        if comments <= 5:
            return 100.0
        return max(20.0, 100 - (comments - 5) * 6)

    @staticmethod
    def _difficulty(candidate: Candidate) -> tuple[str, int]:
        text = f"{candidate.title} {candidate.body}".lower()
        hard = ("refactor", "architecture", "breaking", "migration", "performance", "security")
        easy = ("typo", "documentation", "docs", "readme", "small", "good first issue")
        if any(word in text for word in hard):
            return "hard", 360
        if any(word in text for word in easy) or candidate.repo_size_kb < 5_000:
            return "easy", 60
        return "medium", 180

