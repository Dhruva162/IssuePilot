from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from issuepilot.models import IssueRecord


class BundleService:
    def generate(self, issue: IssueRecord, repository_path: Path, tasks_dir: Path) -> Path:
        bundle = tasks_dir / f"issue{issue.id:03d}"
        bundle.mkdir(parents=True, exist_ok=True)
        metadata = issue.repository_metadata
        self._write(bundle / "issue.md", self._issue(issue))
        self._write(bundle / "context.md", self._context(issue, repository_path))
        self._write(bundle / "repository_summary.md", self._summary(issue, metadata))
        self._write(bundle / "architecture.md", self._architecture(metadata))
        self._write(bundle / "commands.md", self._commands(metadata))
        self._write(bundle / "relevant_files.md", self._relevant_files(repository_path, issue))
        (bundle / "priority.json").write_text(
            json.dumps(
                {
                    "score": issue.score,
                    "difficulty": issue.difficulty,
                    "estimated_minutes": issue.estimated_minutes,
                    "acceptance_probability": issue.acceptance_probability,
                    "factors": issue.ranking_factors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self._write(repository_path / ".issuepilot-prompt.md", self._prompt(issue, bundle))
        return bundle

    @staticmethod
    def _write(path: Path, value: str) -> None:
        path.write_text(value.rstrip() + "\n", encoding="utf-8")

    @staticmethod
    def _issue(issue: IssueRecord) -> str:
        labels = ", ".join(issue.labels) or "none"
        return (
            f"# {issue.title}\n\n"
            f"- Repository: [{issue.repository}]({issue.repository_url})\n"
            f"- Issue: [#{issue.number}]({issue.issue_url})\n"
            f"- Labels: {labels}\n\n## Description\n\n{issue.body or '*No description supplied.*'}"
        )

    @staticmethod
    def _context(issue: IssueRecord, repository_path: Path) -> str:
        return (
            "# Codex task context\n\n"
            f"Work in `{repository_path}` and solve GitHub issue #{issue.number}: "
            f"**{issue.title}**.\n\n"
            "Read every file in this bundle before editing. Inspect the repository's own "
            "contribution instructions. Make the smallest maintainable change, add or update "
            "tests, run the documented validation commands, and summarize changes and any "
            "remaining risk. Do not publish or create a pull request without explicit approval."
        )

    @staticmethod
    def _summary(issue: IssueRecord, metadata: dict[str, Any]) -> str:
        return (
            f"# Repository summary\n\n"
            f"- Repository: {issue.repository}\n"
            f"- Primary language: {metadata.get('language') or 'Unknown'}\n"
            f"- Framework: {metadata.get('framework') or 'Not detected'}\n"
            f"- Package manager: {metadata.get('package_manager') or 'Not detected'}\n"
            f"- Formatter: {', '.join(metadata.get('formatter', [])) or 'Not detected'}\n"
            f"- Linter: {', '.join(metadata.get('linter', [])) or 'Not detected'}\n"
            f"- Tests: {metadata.get('test_framework') or 'Not detected'}\n"
            f"- CI: {', '.join(metadata.get('ci', [])) or 'Not detected'}\n"
            f"- Important directories: "
            f"{', '.join(metadata.get('important_directories', [])) or 'None detected'}"
        )

    @staticmethod
    def _architecture(metadata: dict[str, Any]) -> str:
        architecture = metadata.get("architecture", {})
        edges = architecture.get("edges", [])
        tree = "\n".join(f"- `{edge['from']}` → `{edge['to']}`" for edge in edges)
        return "# Architecture\n\nDetected directory relationships:\n\n" + (
            tree or "- No structure detected"
        )

    @staticmethod
    def _commands(metadata: dict[str, Any]) -> str:
        commands = metadata.get("commands", {})
        body = "\n".join(
            f"- {purpose.title()}: `{command}`" for purpose, command in commands.items()
        )
        return "# Commands\n\n" + (
            body or "No reliable commands were detected. Inspect project documentation."
        )

    @staticmethod
    def _relevant_files(repository_path: Path, issue: IssueRecord) -> str:
        tokens = {
            token.lower()
            for token in issue.title.replace("-", " ").replace("_", " ").split()
            if len(token) >= 4
        }
        ignored = {".git", "node_modules", ".venv", "dist", "build", "vendor"}
        scored: list[tuple[int, str]] = []
        for path in repository_path.rglob("*"):
            if not path.is_file() or any(part in ignored for part in path.parts):
                continue
            relative = path.relative_to(repository_path).as_posix()
            score = sum(token in relative.lower() for token in tokens)
            if score:
                scored.append((score, relative))
        files = [name for _, name in sorted(scored, reverse=True)[:30]]
        content = "\n".join(f"- `{name}`" for name in files)
        return "# Potentially relevant files\n\n" + (
            content or "No filename matches found. Use repository search from the issue vocabulary."
        )

    @staticmethod
    def _prompt(issue: IssueRecord, bundle: Path) -> str:
        return (
            f"Solve GitHub issue #{issue.number} in {issue.repository}: {issue.title}.\n\n"
            f"Start by reading the prepared context bundle at {bundle}, especially issue.md, "
            "context.md, commands.md, and relevant_files.md. Follow repository instructions, "
            "implement a focused fix with tests, and run validation. Do not create or publish "
            "a PR without asking me first."
        )
