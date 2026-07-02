from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from issuepilot.models import IssueRecord, IssueStatus
from issuepilot.schemas import SolveResult

logger = logging.getLogger(__name__)


class SolveService:
    def prepare_and_launch(self, issue: IssueRecord) -> SolveResult:
        if not issue.repo_path or not issue.bundle_path:
            raise ValueError("Issue has not been prepared. Run `issuepilot overnight` first.")
        workspace = Path(issue.repo_path)
        prompt_path = workspace / ".issuepilot-prompt.md"
        if not workspace.is_dir() or not prompt_path.is_file():
            raise ValueError("Prepared workspace is missing. Run the overnight scan again.")
        prompt = prompt_path.read_text(encoding="utf-8")
        codex = shutil.which("codex")
        if codex:
            self._launch_codex(codex, workspace, prompt)
            issue.status = IssueStatus.SOLVING.value
            return SolveResult(
                launched=True,
                method="codex-cli",
                message="Codex launched with the prepared workspace and prompt.",
                workspace_path=str(workspace),
                prompt_path=str(prompt_path),
            )

        launcher = self._write_launcher(workspace, prompt_path)
        self._open_workspace(workspace)
        return SolveResult(
            launched=False,
            method="launcher-file",
            message=(
                "Codex CLI was not found. The workspace was opened and a one-click launcher "
                f"was created at {launcher}. Install/login to Codex CLI, then run that launcher."
            ),
            workspace_path=str(workspace),
            prompt_path=str(prompt_path),
        )

    @staticmethod
    def is_codex_available() -> bool:
        return shutil.which("codex") is not None

    @staticmethod
    def _launch_codex(codex: str, workspace: Path, prompt: str) -> None:
        command = [codex, "-C", str(workspace), "--sandbox", "workspace-write", prompt]
        kwargs: dict[str, object] = {"cwd": workspace}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        else:
            terminal = SolveService._terminal()
            if terminal:
                command = [*terminal, *command]
            kwargs["start_new_session"] = True
        logger.info("Launching Codex in %s", workspace)
        subprocess.Popen(command, **kwargs)

    @staticmethod
    def _terminal() -> list[str] | None:
        options = (
            ("x-terminal-emulator", "-e"),
            ("gnome-terminal", "--"),
            ("konsole", "-e"),
            ("open", "-a", "Terminal"),
        )
        for executable, *args in options:
            if shutil.which(executable):
                return [executable, *args]
        return None

    @staticmethod
    def _write_launcher(workspace: Path, prompt_path: Path) -> Path:
        if os.name == "nt":
            launcher = workspace / "Start IssuePilot Codex.cmd"
            launcher.write_text(
                "@echo off\r\n"
                "where codex >nul 2>nul || (echo Codex CLI is not installed or not on PATH. "
                "& pause & exit /b 1)\r\n"
                f'cd /d "{workspace}"\r\n'
                f'codex -C "{workspace}" --sandbox workspace-write '
                f'"Read and follow the prepared prompt at {prompt_path}"\r\n',
                encoding="utf-8",
            )
        else:
            launcher = workspace / "start-issuepilot-codex.sh"
            launcher.write_text(
                "#!/usr/bin/env sh\nset -eu\n"
                f"cd {shlex.quote(str(workspace))}\n"
                f"codex -C {shlex.quote(str(workspace))} --sandbox workspace-write "
                f"{shlex.quote(f'Read and follow the prepared prompt at {prompt_path}')}\n",
                encoding="utf-8",
            )
            launcher.chmod(0o755)
        return launcher

    @staticmethod
    def _open_workspace(workspace: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(workspace)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(workspace)], start_new_session=True)
            else:
                subprocess.Popen(["xdg-open", str(workspace)], start_new_session=True)
        except OSError:
            logger.warning("Could not open workspace automatically: %s", workspace)
