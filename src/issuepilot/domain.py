from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Candidate:
    github_id: int
    number: int
    repository: str
    repository_url: str
    clone_url: str
    title: str
    body: str
    issue_url: str
    labels: list[str]
    stars: int
    comments: int
    issue_created_at: datetime
    repo_pushed_at: datetime | None
    maintainer_activity: float
    has_tests: bool
    has_ci: bool
    repo_size_kb: int


@dataclass(frozen=True, slots=True)
class Ranking:
    score: float
    difficulty: str
    estimated_minutes: int
    acceptance_probability: float
    factors: dict[str, float]

