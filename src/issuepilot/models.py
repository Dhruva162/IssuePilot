from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from issuepilot.db import Base


class IssueStatus(StrEnum):
    READY = "ready"
    FAVORITE = "favorite"
    SKIPPED = "skipped"
    ARCHIVED = "archived"
    SOLVING = "solving"


class IssueRecord(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    number: Mapped[int]
    repository: Mapped[str] = mapped_column(String(255), index=True)
    repository_url: Mapped[str] = mapped_column(String(500))
    clone_url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, default="")
    issue_url: Mapped[str] = mapped_column(String(500))
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    stars: Mapped[int] = mapped_column(default=0)
    comments: Mapped[int] = mapped_column(default=0)
    score: Mapped[float] = mapped_column(Float, default=0)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    estimated_minutes: Mapped[int] = mapped_column(default=120)
    acceptance_probability: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(20), default=IssueStatus.READY.value)
    has_tests: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ci: Mapped[bool] = mapped_column(Boolean, default=False)
    repo_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    bundle_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    repository_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ranking_factors: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    issue_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    repo_pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

