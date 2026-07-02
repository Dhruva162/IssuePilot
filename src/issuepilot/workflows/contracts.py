from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ValidationResult:
    passed: bool
    output: str


class Validator(Protocol):
    def validate(self, repository: Path) -> ValidationResult: ...


class TestRunner(Protocol):
    def run(self, repository: Path, command: str) -> ValidationResult: ...


class PullRequestPublisher(Protocol):
    def publish(self, repository: Path, title: str, body: str) -> str: ...


class ApprovalGate(Protocol):
    def approved(self, action: str, summary: str) -> bool: ...

