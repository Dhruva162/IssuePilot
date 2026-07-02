from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv

from issuepilot.models import IssueRecord, IssueStatus
from issuepilot.schemas import SolveResult

logger = logging.getLogger(__name__)

CODEX_ENV_VAR = "ISSUEPILOT_CODEX_CLI"


class SolveService:
    def prepare_and_launch(self, issue: IssueRecord) -> SolveResult:
        if not issue.repo_path or not issue.bundle_path:
            raise ValueError("Issue has not been prepared. Run `issuepilot overnight` first.")
        workspace = Path(issue.repo_path)
        prompt_path = workspace / ".issuepilot-prompt.md"
        if not workspace.is_dir() or not prompt_path.is_file():
            raise ValueError("Prepared workspace is missing. Run the overnight scan again.")
        prompt = self._prompt_instruction(prompt_path)
        codex = self._find_codex_cli()
        if codex:
            try:
                self._launch_codex(codex, workspace, prompt)
                issue.status = IssueStatus.SOLVING.value
                return SolveResult(
                    launched=True,
                    method="codex-cli",
                    message="Codex launched with the prepared workspace and generated prompt.",
                    workspace_path=str(workspace),
                    prompt_path=str(prompt_path),
                )
            except OSError as exc:
                logger.warning(
                    "Codex CLI was detected at %s but could not be launched: %s",
                    codex,
                    exc,
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
        return SolveService._find_codex_cli() is not None

    @staticmethod
    def _find_codex_cli() -> str | None:
        load_dotenv()
        configured = os.getenv(CODEX_ENV_VAR)
        if configured:
            configured_path = Path(configured).expanduser()
            if configured_path.is_file():
                return str(configured_path)
            logger.warning("%s points to a missing Codex executable: %s", CODEX_ENV_VAR, configured)

        for executable in ("codex", "codex.cmd", "codex.exe", "codex.bat"):
            resolved = shutil.which(executable)
            if resolved:
                return resolved

        for candidate in SolveService._windows_codex_candidates():
            if candidate.is_file():
                return str(candidate)
        return None

    @staticmethod
    def _windows_codex_candidates() -> Iterable[Path]:
        if os.name != "nt":
            return ()

        candidates: list[Path] = []
        appdata = os.getenv("APPDATA")
        if appdata:
            npm_bin = Path(appdata) / "npm"
            candidates.extend(
                [
                    npm_bin / "codex.cmd",
                    npm_bin / "codex.exe",
                    npm_bin / "codex.bat",
                ]
            )
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            candidates.extend(
                [
                    Path(local_appdata) / "Programs" / "Codex" / "codex.exe",
                    Path(local_appdata) / "Microsoft" / "WinGet" / "Links" / "codex.exe",
                    Path(local_appdata) / "Microsoft" / "WinGet" / "Links" / "codex.cmd",
                ]
            )
        return candidates

    @staticmethod
    def _prompt_instruction(prompt_path: Path) -> str:
        return f"Read and follow the prepared IssuePilot prompt at {prompt_path}"

    @staticmethod
    def _launch_codex(codex: str, workspace: Path, prompt: str) -> None:
        command = [
            codex,
            "-C",
            str(workspace),
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "on-request",
            prompt,
        ]
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
                f'codex -C "{workspace}" --sandbox workspace-write --ask-for-approval on-request '
                f'"{SolveService._prompt_instruction(prompt_path)}"\r\n',
                encoding="utf-8",
            )
        else:
            launcher = workspace / "start-issuepilot-codex.sh"
            launcher.write_text(
                "#!/usr/bin/env sh\nset -eu\n"
                f"cd {shlex.quote(str(workspace))}\n"
                f"codex -C {shlex.quote(str(workspace))} --sandbox workspace-write "
                "--ask-for-approval on-request "
                f"{shlex.quote(SolveService._prompt_instruction(prompt_path))}\n",
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
