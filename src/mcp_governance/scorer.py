"""Tool Graph Capability Score: composite quality/security score per tool."""

from __future__ import annotations

from typing import Any

from .linter import lint
from .models import LintIssue, Severity, ToolScore
from .security import check_security


def _score_description(tool: dict[str, Any]) -> int:
    """0–30 pts for description quality."""
    desc = (tool.get("description") or "").strip()
    if not desc:
        return 0
    length_score = min(20, len(desc) // 5)  # up to 20 pts for length (100 chars → 20)
    # Bonus for having example or structured detail
    detail_bonus = 5 if any(kw in desc.lower() for kw in ("example", "returns", "e.g.", "e.g,", "i.e.")) else 0
    # Penalty for vague openers
    import re
    vague = re.compile(r"^(does|performs|runs|executes|calls|handles|processes)\b", re.IGNORECASE)
    vague_penalty = -5 if vague.match(desc) else 0
    return max(0, min(30, length_score + detail_bonus + vague_penalty))


def _score_parameters(tool: dict[str, Any], lint_issues: list[LintIssue]) -> int:
    """0–30 pts for parameter quality."""
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    if not properties:
        return 25  # no params → not penalised but not rewarded

    tool_name = tool.get("name", "")
    param_errors = sum(
        1 for i in lint_issues
        if i.tool == tool_name
        and i.code in ("L020", "L021", "L022")
        and i.severity == Severity.ERROR
    )
    param_warnings = sum(
        1 for i in lint_issues
        if i.tool == tool_name
        and i.code in ("L020", "L021", "L022", "L030", "L031")
        and i.severity == Severity.WARNING
    )
    score = 30 - (param_errors * 10) - (param_warnings * 3)
    return max(0, min(30, score))


def _score_type_strictness(tool: dict[str, Any]) -> int:
    """0–20 pts for JSON Schema type strictness."""
    schema = tool.get("inputSchema", {})
    if not isinstance(schema, dict):
        return 0
    properties = schema.get("properties", {})
    if not isinstance(properties, dict) or not properties:
        return 15

    strict_count = 0
    total = len(properties)
    for param_schema in properties.values():
        if not isinstance(param_schema, dict):
            continue
        has_type = "type" in param_schema or "enum" in param_schema or "$ref" in param_schema
        has_constraint = any(
            k in param_schema
            for k in ("minimum", "maximum", "minLength", "maxLength", "pattern", "enum", "properties", "items")
        )
        if has_type:
            strict_count += 1
        if has_constraint:
            strict_count += 1

    return min(20, round((strict_count / (total * 2)) * 20))


def _score_security(tool: dict[str, Any], all_security_issues: list) -> int:
    """0–20 pts for security posture."""
    name = tool.get("name", "")
    tool_errors = sum(1 for i in all_security_issues if i.tool == name and i.severity == Severity.ERROR)
    tool_warnings = sum(1 for i in all_security_issues if i.tool == name and i.severity == Severity.WARNING)
    score = 20 - (tool_errors * 10) - (tool_warnings * 4)
    return max(0, min(20, score))


def score(schema: dict[str, Any]) -> list[ToolScore]:
    """Compute a ToolScore for each tool in the schema."""
    lint_issues = lint(schema)
    security_issues = check_security(schema)
    scores: list[ToolScore] = []

    for tool in schema.get("tools", []):
        if not isinstance(tool, dict):
            continue
        name = tool.get("name", "<unnamed>")
        scores.append(
            ToolScore(
                tool=name,
                description_score=_score_description(tool),
                parameter_score=_score_parameters(tool, lint_issues),
                type_strictness_score=_score_type_strictness(tool),
                security_score=_score_security(tool, security_issues),
            )
        )
    return scores
