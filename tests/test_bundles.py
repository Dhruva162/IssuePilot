from datetime import UTC, datetime

from issuepilot.models import IssueRecord
from issuepilot.services.bundles import BundleService


def test_bundle_contains_required_files_and_prompt(tmp_path):
    repository = tmp_path / "repo"
    tasks = tmp_path / "tasks"
    repository.mkdir()
    (repository / "parser.py").write_text("def parse(): pass", encoding="utf-8")
    issue = IssueRecord(
        id=1,
        github_id=10,
        number=7,
        repository="owner/repo",
        repository_url="https://github.com/owner/repo",
        clone_url="https://github.com/owner/repo.git",
        title="Fix parser behavior",
        body="Parser fails on empty input.",
        issue_url="https://github.com/owner/repo/issues/7",
        labels=["bug"],
        stars=100,
        comments=1,
        score=80,
        difficulty="medium",
        estimated_minutes=180,
        acceptance_probability=0.7,
        repository_metadata={
            "language": "Python",
            "commands": {"test": "pytest"},
            "architecture": {"edges": [{"from": "repository", "to": "src"}]},
        },
        ranking_factors={"stars": 50},
        issue_created_at=datetime.now(UTC),
    )
    bundle = BundleService().generate(issue, repository, tasks)
    required = {
        "issue.md",
        "context.md",
        "repository_summary.md",
        "architecture.md",
        "commands.md",
        "relevant_files.md",
        "priority.json",
    }
    assert {path.name for path in bundle.iterdir()} == required
    assert (repository / ".issuepilot-prompt.md").exists()
    assert "pytest" in (bundle / "commands.md").read_text(encoding="utf-8")

