from datetime import UTC, datetime

import pytest

from issuepilot.models import IssueRecord
from issuepilot.services.solve import SolveService


def test_solve_rejects_unprepared_issue():
    issue = IssueRecord(
        github_id=1,
        number=1,
        repository="owner/repo",
        repository_url="https://github.com/owner/repo",
        clone_url="https://github.com/owner/repo.git",
        title="Issue",
        body="",
        issue_url="https://github.com/owner/repo/issues/1",
        issue_created_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="not been prepared"):
        SolveService().prepare_and_launch(issue)

