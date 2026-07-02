from datetime import UTC, datetime, timedelta

from issuepilot.domain import Candidate
from issuepilot.services.ranking import RankingService


def candidate(**overrides):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    values = {
        "github_id": 1,
        "number": 12,
        "repository": "owner/repo",
        "repository_url": "https://github.com/owner/repo",
        "clone_url": "https://github.com/owner/repo.git",
        "title": "Fix parser edge case",
        "body": "A focused bug in the parser.",
        "issue_url": "https://github.com/owner/repo/issues/12",
        "labels": ["good first issue"],
        "stars": 2_000,
        "comments": 2,
        "issue_created_at": now - timedelta(days=20),
        "repo_pushed_at": now - timedelta(days=2),
        "maintainer_activity": 90.0,
        "has_tests": True,
        "has_ci": True,
        "repo_size_kb": 20_000,
    }
    values.update(overrides)
    return Candidate(**values)


def test_ranking_is_bounded_and_explained():
    ranking = RankingService().rank(candidate(), datetime(2026, 1, 1, tzinfo=UTC))
    assert 0 <= ranking.score <= 100
    assert set(ranking.factors) == {
        "stars",
        "recent_commits",
        "maintainer_activity",
        "tests",
        "ci",
        "issue_age",
        "comments",
    }
    assert ranking.acceptance_probability <= 0.95


def test_healthy_repository_outranks_inactive_repository():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    healthy = RankingService().rank(candidate(), now)
    inactive = RankingService().rank(
        candidate(
            stars=5,
            comments=30,
            repo_pushed_at=now - timedelta(days=400),
            maintainer_activity=0,
            has_tests=False,
            has_ci=False,
        ),
        now,
    )
    assert healthy.score > inactive.score


def test_documentation_issue_is_estimated_easy():
    ranking = RankingService().rank(
        candidate(title="Fix README typo"),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert ranking.difficulty == "easy"
    assert ranking.estimated_minutes == 60

