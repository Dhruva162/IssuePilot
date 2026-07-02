from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    workspace_dir: Path
    tasks_dir: Path
    github_token: str | None
    github_query: str
    max_issues: int
    min_stars: int
    max_repo_size_kb: int
    log_level: str
    frontend_url: str
    api_url: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        return cls(
            database_url=os.getenv(
                "ISSUEPILOT_DATABASE_URL", "sqlite:///./data/issuepilot.db"
            ),
            workspace_dir=_path(os.getenv("ISSUEPILOT_WORKSPACE", "./workspaces")),
            tasks_dir=_path(os.getenv("ISSUEPILOT_TASKS_DIR", "./tasks")),
            github_token=os.getenv("GITHUB_TOKEN") or None,
            github_query=os.getenv(
                "ISSUEPILOT_GITHUB_QUERY",
                'is:issue is:open label:"good first issue" archived:false',
            ),
            max_issues=max(1, int(os.getenv("ISSUEPILOT_MAX_ISSUES", "10"))),
            min_stars=max(0, int(os.getenv("ISSUEPILOT_MIN_STARS", "100"))),
            max_repo_size_kb=max(
                1, int(os.getenv("ISSUEPILOT_MAX_REPO_SIZE_KB", "500000"))
            ),
            log_level=os.getenv("ISSUEPILOT_LOG_LEVEL", "INFO").upper(),
            frontend_url=os.getenv("ISSUEPILOT_FRONTEND_URL", "http://localhost:5173"),
            api_url=os.getenv("ISSUEPILOT_API_URL", "http://127.0.0.1:8000"),
        )

    def ensure_directories(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            Path(self.database_url.removeprefix("sqlite:///")).resolve().parent.mkdir(
                parents=True, exist_ok=True
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_directories()
    return settings

