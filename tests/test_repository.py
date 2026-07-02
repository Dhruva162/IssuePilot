import json

from issuepilot.services.repository import RepositoryService


def test_analyzer_detects_typescript_toolchain(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "src" / "App.tsx").write_text("export const App = () => null", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "eslint.config.js").write_text("export default []", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^19"},
                "devDependencies": {"vitest": "^2"},
                "scripts": {"test": "vitest", "lint": "eslint ."},
            }
        ),
        encoding="utf-8",
    )

    metadata = RepositoryService().analyze(tmp_path)

    assert metadata["language"] == "TypeScript"
    assert metadata["framework"] == "React"
    assert metadata["package_manager"] == "npm"
    assert metadata["test_framework"] == "Vitest"
    assert metadata["ci"] == ["GitHub Actions"]
    assert metadata["commands"]["test"] == "npm run test"
    assert "src" in metadata["important_directories"]


def test_analyzer_handles_unknown_repository(tmp_path):
    (tmp_path / "README.md").write_text("# Minimal", encoding="utf-8")
    metadata = RepositoryService().analyze(tmp_path)
    assert metadata["language"] == "Unknown"
    assert metadata["framework"] is None
    assert metadata["commands"] == {}

