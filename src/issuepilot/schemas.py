from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    repository: str
    repository_url: str
    title: str
    issue_url: str
    labels: list[str]
    stars: int
    comments: int
    score: float
    difficulty: str
    estimated_minutes: int
    acceptance_probability: float
    status: str
    has_tests: bool
    has_ci: bool
    bundle_path: str | None
    repository_metadata: dict[str, Any]
    ranking_factors: dict[str, float]
    issue_created_at: datetime
    scanned_at: datetime


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(ready|favorite|skipped|archived)$")


class SolveResult(BaseModel):
    launched: bool
    method: str
    message: str
    workspace_path: str
    prompt_path: str


class OvernightResult(BaseModel):
    discovered: int
    prepared: int
    failed: int
    issue_ids: list[int]


class HealthResult(BaseModel):
    status: str
    database: str
    codex_available: bool
