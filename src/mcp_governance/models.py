"""Shared data models for audit reports."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintIssue(BaseModel):
    tool: str
    field: str
    severity: Severity
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.tool}.{self.field} ({self.code}): {self.message}"


class SecurityIssue(BaseModel):
    tool: str
    severity: Severity
    code: str
    message: str
    detail: str = ""

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.tool} ({self.code}): {self.message}"


class ToolScore(BaseModel):
    tool: str
    description_score: int = Field(ge=0, le=30)
    parameter_score: int = Field(ge=0, le=30)
    type_strictness_score: int = Field(ge=0, le=20)
    security_score: int = Field(ge=0, le=20)

    @property
    def total(self) -> int:
        return (
            self.description_score
            + self.parameter_score
            + self.type_strictness_score
            + self.security_score
        )

    @property
    def grade(self) -> str:
        t = self.total
        if t >= 90:
            return "A"
        if t >= 75:
            return "B"
        if t >= 60:
            return "C"
        if t >= 40:
            return "D"
        return "F"


class AuditReport(BaseModel):
    server_name: str
    tool_count: int
    lint_issues: list[LintIssue] = Field(default_factory=list)
    security_issues: list[SecurityIssue] = Field(default_factory=list)
    tool_scores: list[ToolScore] = Field(default_factory=list)

    @property
    def overall_score(self) -> int:
        if not self.tool_scores:
            return 0
        return round(sum(s.total for s in self.tool_scores) / len(self.tool_scores))

    @property
    def overall_grade(self) -> str:
        t = self.overall_score
        if t >= 90:
            return "A"
        if t >= 75:
            return "B"
        if t >= 60:
            return "C"
        if t >= 40:
            return "D"
        return "F"

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.lint_issues if i.severity == Severity.ERROR) + sum(
            1 for i in self.security_issues if i.severity == Severity.ERROR
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for i in self.lint_issues if i.severity == Severity.WARNING
        ) + sum(
            1 for i in self.security_issues if i.severity == Severity.WARNING
        )
