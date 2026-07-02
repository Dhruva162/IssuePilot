from datetime import UTC, datetime
from pathlib import Path

import pytest

from issuepilot.models import IssueRecord, IssueStatus
from issuepilot.services.solve import SolveService


def issue_record(**overrides: object) -> IssueRecord:
    values = {
        "github_id": 1,
        "number": 1,
        "repository": "owner/repo",
        "repository_url": "https://github.com/owner/repo",
        "clone_url": "https://github.com/owner/repo.git",
        "title": "Issue",
        "body": "",
        "issue_url": "https://github.com/owner/repo/issues/1",
        "issue_created_at": datetime.now(UTC),
    }
    values.update(overrides)
    return IssueRecord(**values)


def test_solve_rejects_unprepared_issue():
    issue = issue_record()
    with pytest.raises(ValueError, match="not been prepared"):
        SolveService().prepare_and_launch(issue)


def test_solve_launches_codex_cli_when_available(tmp_path, monkeypatch):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    prompt_path = workspace / ".issuepilot-prompt.md"
    prompt_path.write_text("prepared prompt", encoding="utf-8")
    issue = issue_record(repo_path=str(workspace), bundle_path=str(tmp_path / "task"))
    launched: dict[str, object] = {}

    def fake_launch(codex: str, launch_workspace: Path, prompt: str) -> None:
        launched["codex"] = codex
        launched["workspace"] = launch_workspace
        launched["prompt"] = prompt

    monkeypatch.setattr(
        SolveService,
        "_find_codex_cli",
        staticmethod(lambda: "C:\\Tools\\codex.cmd"),
    )
    monkeypatch.setattr(SolveService, "_launch_codex", staticmethod(fake_launch))
    monkeypatch.setattr(
        SolveService,
        "_open_workspace",
        staticmethod(lambda workspace: pytest.fail("fallback opened")),
    )

    result = SolveService().prepare_and_launch(issue)

    assert result.launched is True
    assert result.method == "codex-cli"
    assert issue.status == IssueStatus.SOLVING.value
    assert launched == {
        "codex": "C:\\Tools\\codex.cmd",
        "workspace": workspace,
        "prompt": f"Read and follow the prepared IssuePilot prompt at {prompt_path}",
    }


def test_solve_falls_back_when_codex_is_unavailable(tmp_path, monkeypatch):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    prompt_path = workspace / ".issuepilot-prompt.md"
    prompt_path.write_text("prepared prompt", encoding="utf-8")
    issue = issue_record(repo_path=str(workspace), bundle_path=str(tmp_path / "task"))
    opened: list[Path] = []

    monkeypatch.setattr(SolveService, "_find_codex_cli", staticmethod(lambda: None))
    monkeypatch.setattr(
        SolveService,
        "_open_workspace",
        staticmethod(lambda workspace: opened.append(workspace)),
    )

    result = SolveService().prepare_and_launch(issue)

    assert result.launched is False
    assert result.method == "launcher-file"
    assert opened == [workspace]
    launcher_names = {"Start IssuePilot Codex.cmd", "start-issuepilot-codex.sh"}
    assert any((workspace / launcher_name).exists() for launcher_name in launcher_names)


def test_solve_falls_back_when_codex_launch_fails(tmp_path, monkeypatch):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    prompt_path = workspace / ".issuepilot-prompt.md"
    prompt_path.write_text("prepared prompt", encoding="utf-8")
    issue = issue_record(repo_path=str(workspace), bundle_path=str(tmp_path / "task"))
    opened: list[Path] = []

    monkeypatch.setattr(SolveService, "_find_codex_cli", staticmethod(lambda: "codex"))
    monkeypatch.setattr(
        SolveService,
        "_launch_codex",
        staticmethod(lambda codex, workspace, prompt: (_ for _ in ()).throw(OSError("boom"))),
    )
    monkeypatch.setattr(
        SolveService,
        "_open_workspace",
        staticmethod(lambda workspace: opened.append(workspace)),
    )

    result = SolveService().prepare_and_launch(issue)

    assert result.launched is False
    assert result.method == "launcher-file"
    assert issue.status != IssueStatus.SOLVING.value
    assert opened == [workspace]
