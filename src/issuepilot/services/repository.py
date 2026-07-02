from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import networkx as nx
from git import Repo

logger = logging.getLogger(__name__)


class RepositoryService:
    def clone_or_update(self, clone_url: str, repository: str, root: Path) -> Path:
        destination = root / repository.replace("/", "__")
        if (destination / ".git").exists():
            logger.info("Updating %s", repository)
            repo = Repo(destination)
            repo.remotes.origin.fetch(depth=1)
            default_ref = repo.remotes.origin.refs[0]
            repo.git.reset("--hard", default_ref.name)
        else:
            if destination.exists():
                shutil.rmtree(destination)
            logger.info("Cloning %s", repository)
            Repo.clone_from(clone_url, destination, depth=1)
        return destination

    def analyze(self, path: Path) -> dict[str, Any]:
        files = self._files(path)
        names = {file.name.lower() for file in files}
        relative = {file.relative_to(path).as_posix() for file in files}
        metadata: dict[str, Any] = {
            "language": self._language(files),
            "framework": self._framework(path, names),
            "package_manager": self._package_manager(names),
            "formatter": self._detect(names, {
                "ruff": {"ruff.toml", ".ruff.toml"},
                "prettier": {".prettierrc", ".prettierrc.json", "prettier.config.js"},
                "black": {"pyproject.toml"},
                "gofmt": {"go.mod"},
                "rustfmt": {"rustfmt.toml"},
            }),
            "linter": self._detect(names, {
                "ruff": {"ruff.toml", ".ruff.toml", "pyproject.toml"},
                "eslint": {"eslint.config.js", ".eslintrc", ".eslintrc.json"},
                "golangci-lint": {".golangci.yml"},
                "clippy": {"cargo.toml"},
            }),
            "test_framework": self._test_framework(path, names),
            "ci": self._ci(relative),
            "important_directories": self._important_directories(path),
            "commands": self._commands(path, names),
        }
        metadata["architecture"] = self._architecture(path)
        return metadata

    @staticmethod
    def _files(path: Path) -> list[Path]:
        ignored = {".git", "node_modules", ".venv", "dist", "build", "vendor"}
        return [
            item
            for item in path.rglob("*")
            if item.is_file()
            and not any(part in ignored for part in item.relative_to(path).parts)
        ][:20_000]

    @staticmethod
    def _language(files: list[Path]) -> str:
        extensions = {
            ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
            ".js": "JavaScript", ".jsx": "JavaScript", ".go": "Go",
            ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
            ".cs": "C#", ".cpp": "C++", ".c": "C",
        }
        counts: dict[str, float] = {}
        for file in files:
            language = extensions.get(file.suffix.lower())
            if language:
                # Configuration files should not outweigh application source. JSX/TSX
                # also carry more signal than a single build configuration file.
                is_config = "config" in file.stem.lower() or file.name.startswith(".")
                weight = 0.25 if is_config else (2.0 if file.suffix in {".tsx", ".jsx"} else 1.0)
                counts[language] = counts.get(language, 0) + weight
        return max(counts, key=counts.get) if counts else "Unknown"

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _framework(self, path: Path, names: set[str]) -> str | None:
        package = self._read_json(path / "package.json")
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        for dependency, framework in (
            ("next", "Next.js"), ("react", "React"), ("vue", "Vue"),
            ("@angular/core", "Angular"), ("svelte", "Svelte"),
        ):
            if dependency in deps:
                return framework
        text = self._safe_text(path / "pyproject.toml") + self._safe_text(path / "requirements.txt")
        for dependency, framework in (
            ("fastapi", "FastAPI"), ("django", "Django"), ("flask", "Flask"),
        ):
            if dependency in text.lower():
                return framework
        if "cargo.toml" in names:
            return "Rust"
        return None

    @staticmethod
    def _package_manager(names: set[str]) -> str | None:
        for marker, manager in (
            ("uv.lock", "uv"), ("poetry.lock", "Poetry"), ("pyproject.toml", "pip"),
            ("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "Yarn"),
            ("package-lock.json", "npm"), ("cargo.toml", "Cargo"),
            ("go.mod", "Go modules"), ("pom.xml", "Maven"), ("build.gradle", "Gradle"),
        ):
            if marker in names:
                return manager
        return None

    @staticmethod
    def _detect(names: set[str], options: dict[str, set[str]]) -> list[str]:
        return [tool for tool, markers in options.items() if names & markers]

    def _test_framework(self, path: Path, names: set[str]) -> str | None:
        package = self._read_json(path / "package.json")
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        for dependency, framework in (
            ("vitest", "Vitest"), ("jest", "Jest"), ("mocha", "Mocha"),
            ("playwright", "Playwright"),
        ):
            if dependency in deps:
                return framework
        pyproject = self._safe_text(path / "pyproject.toml").lower()
        if "pytest" in pyproject or "pytest.ini" in names:
            return "Pytest"
        if "cargo.toml" in names:
            return "Cargo test"
        if "go.mod" in names:
            return "Go test"
        return None

    @staticmethod
    def _ci(relative: set[str]) -> list[str]:
        systems = []
        if any(name.startswith(".github/workflows/") for name in relative):
            systems.append("GitHub Actions")
        if ".gitlab-ci.yml" in relative:
            systems.append("GitLab CI")
        if "circle.yml" in relative or ".circleci/config.yml" in relative:
            systems.append("CircleCI")
        return systems

    @staticmethod
    def _important_directories(path: Path) -> list[str]:
        preferred = {
            "src", "lib", "app", "packages", "tests", "test", "docs",
            "scripts", "api", "server", "client", "frontend", "backend",
        }
        return sorted(
            item.name for item in path.iterdir() if item.is_dir() and item.name.lower() in preferred
        )

    def _commands(self, path: Path, names: set[str]) -> dict[str, str]:
        package = self._read_json(path / "package.json")
        scripts = package.get("scripts", {})
        commands: dict[str, str] = {}
        for purpose in ("test", "lint", "format", "build"):
            if purpose in scripts:
                commands[purpose] = f"npm run {purpose}"
        if "pyproject.toml" in names:
            text = self._safe_text(path / "pyproject.toml").lower()
            if "pytest" in text:
                commands.setdefault("test", "pytest")
            if "ruff" in text:
                commands.setdefault("lint", "ruff check .")
                commands.setdefault("format", "ruff format .")
        if "go.mod" in names:
            commands.update({"test": "go test ./...", "format": "gofmt -w ."})
        if "cargo.toml" in names:
            commands.update({"test": "cargo test", "lint": "cargo clippy"})
        return commands

    def _architecture(self, path: Path) -> dict[str, Any]:
        graph = nx.DiGraph()
        directories = self._important_directories(path)
        graph.add_node("repository")
        for directory in directories:
            graph.add_edge("repository", directory)
            directory_path = path / directory
            for child in list(directory_path.iterdir())[:20]:
                if child.is_dir() and not child.name.startswith("."):
                    graph.add_edge(directory, f"{directory}/{child.name}")
        return {
            "nodes": list(graph.nodes),
            "edges": [{"from": source, "to": target} for source, target in graph.edges],
        }

    @staticmethod
    def _safe_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:100_000]
        except OSError:
            return ""
