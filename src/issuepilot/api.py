from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from issuepilot.config import get_settings
from issuepilot.db import get_session_factory, init_db
from issuepilot.models import IssueRecord
from issuepilot.schemas import HealthResult, IssueOut, SolveResult, StatusUpdate
from issuepilot.services.solve import SolveService


def get_session() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="IssuePilot API",
    version="0.1.0",
    description="Local API for prepared GitHub issues.",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=False,
    allow_methods=["GET", "PATCH", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", response_model=HealthResult)
def health(session: SessionDep) -> HealthResult:
    session.execute(text("SELECT 1"))
    return HealthResult(
        status="ok",
        database="connected",
        codex_available=SolveService.is_codex_available(),
    )


@app.get("/api/issues", response_model=list[IssueOut])
def list_issues(
    session: SessionDep,
    status: str | None = Query(default=None),
) -> list[IssueRecord]:
    query = select(IssueRecord)
    if status:
        query = query.where(IssueRecord.status == status)
    else:
        query = query.where(IssueRecord.status.not_in(("skipped", "archived")))
    return list(session.scalars(query.order_by(IssueRecord.score.desc())).all())


@app.patch("/api/issues/{issue_id}/status", response_model=IssueOut)
def update_status(
    issue_id: int,
    update: StatusUpdate,
    session: SessionDep,
) -> IssueRecord:
    issue = session.get(IssueRecord, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = update.status
    session.commit()
    return issue


@app.post("/api/issues/{issue_id}/solve", response_model=SolveResult)
def solve(issue_id: int, session: SessionDep) -> SolveResult:
    issue = session.get(IssueRecord, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    try:
        result = SolveService().prepare_and_launch(issue)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    session.commit()
    return result


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (frontend_dist / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        requested = frontend_dist / path
        return FileResponse(requested if requested.is_file() else frontend_dist / "index.html")
