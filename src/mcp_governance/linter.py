"""Schema linter: flag quality issues in MCP tool definitions."""

from __future__ import annotations

import re
from typing import Any

from .models import LintIssue, Severity

# Parameter names that are conventionally single-character and acceptable
_CONVENTIONAL_SHORT_NAMES = {"n", "k", "x", "y", "z", "q", "p"}

# Overly vague description starters that signal a low-quality description
_VAGUE_STARTERS = re.compile(
    r"^(does|performs|runs|executes|calls|handles|processes|gets|sets|returns)\b",
    re.IGNORECASE,
)

# Over-broad JSON Schema types (bare, without refinement)
_OVER_BROAD = {"object", "array"}


def _check_tool_description(tool_name: str, tool: dict[str, Any]) -> list[LintIssue]:
    issues: list[LintIssue] = []
    desc = tool.get("description", "")
    if not desc or not desc.strip():
        issues.append(
            LintIssue(
                tool=tool_name,
                field="description",
                severity=Severity.ERROR,
                code="L001",
                message="Tool is missing a description.",
            )
        )
    elif len(desc.strip()) < 20:
        issues.append(
            LintIssue(
                tool=tool_name,
                field="description",
                severity=Severity.WARNING,
                code="L002",
                message=f"Description is very short ({len(desc.strip())} chars); aim for ≥20.",
            )
        )
    elif _VAGUE_STARTERS.match(desc.strip()):
        issues.append(
            LintIssue(
                tool=tool_name,
                field="description",
                severity=Severity.INFO,
                code="L003",
                message="Description starts with a vague verb; prefer a noun-first summary.",
            )
        )
    return issues


def _check_input_schema(tool_name: str, tool: dict[str, Any]) -> list[LintIssue]:
    issues: list[LintIssue] = []
    schema = tool.get("inputSchema", {})
    if not isinstance(schema, dict):
        issues.append(
            LintIssue(
                tool=tool_name,
                field="inputSchema",
                severity=Severity.ERROR,
                code="L010",
                message="inputSchema must be a JSON object.",
            )
        )
        return issues

    if schema.get("type") != "object":
        issues.append(
            LintIssue(
                tool=tool_name,
                field="inputSchema.type",
                severity=Severity.WARNING,
                code="L011",
                message='inputSchema.type should be "object".',
            )
        )

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return issues

    required_fields = schema.get("required", [])

    for param_name, param_schema in properties.items():
        if not isinstance(param_schema, dict):
            continue
        issues.extend(
            _check_parameter(tool_name, param_name, param_schema, required_fields)
        )
    return issues


def _check_parameter(
    tool_name: str,
    param_name: str,
    param_schema: dict[str, Any],
    required_fields: list[str],
) -> list[LintIssue]:
    issues: list[LintIssue] = []
    field_prefix = f"inputSchema.properties.{param_name}"

    # Missing parameter description
    param_desc = param_schema.get("description", "")
    if not param_desc or not param_desc.strip():
        issues.append(
            LintIssue(
                tool=tool_name,
                field=f"{field_prefix}.description",
                severity=Severity.ERROR,
                code="L020",
                message=f'Parameter "{param_name}" is missing a description.',
            )
        )
    elif len(param_desc.strip()) < 10:
        issues.append(
            LintIssue(
                tool=tool_name,
                field=f"{field_prefix}.description",
                severity=Severity.WARNING,
                code="L021",
                message=f'Parameter "{param_name}" description is very short.',
            )
        )

    # Unclear parameter name (too short)
    if len(param_name) == 1 and param_name not in _CONVENTIONAL_SHORT_NAMES:
        issues.append(
            LintIssue(
                tool=tool_name,
                field=f"{field_prefix}",
                severity=Severity.WARNING,
                code="L022",
                message=f'Parameter name "{param_name}" is a single character; use a descriptive name.',
            )
        )

    # Over-broad type without refinement
    param_type = param_schema.get("type")
    if param_type in _OVER_BROAD:
        has_refinement = bool(
            param_schema.get("properties")
            or param_schema.get("items")
            or param_schema.get("additionalProperties")
            or param_schema.get("enum")
        )
        if not has_refinement:
            issues.append(
                LintIssue(
                    tool=tool_name,
                    field=f"{field_prefix}.type",
                    severity=Severity.WARNING,
                    code="L030",
                    message=(
                        f'Parameter "{param_name}" has over-broad type "{param_type}" '
                        "with no properties, items, or enum constraint."
                    ),
                )
            )

    # Integer/number without bounds
    if param_type in ("integer", "number"):
        has_bounds = "minimum" in param_schema or "maximum" in param_schema
        if not has_bounds:
            issues.append(
                LintIssue(
                    tool=tool_name,
                    field=f"{field_prefix}",
                    severity=Severity.INFO,
                    code="L031",
                    message=f'Numeric parameter "{param_name}" has no minimum/maximum bounds.',
                )
            )

    return issues


def lint(schema: dict[str, Any]) -> list[LintIssue]:
    """Run all lint checks on an MCP schema; return a list of issues."""
    issues: list[LintIssue] = []
    tools = schema.get("tools", [])
    seen_names: set[str] = set()

    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name", "<unnamed>")

        if name in seen_names:
            issues.append(
                LintIssue(
                    tool=name,
                    field="name",
                    severity=Severity.ERROR,
                    code="L005",
                    message=f'Duplicate tool name "{name}".',
                )
            )
        seen_names.add(name)

        issues.extend(_check_tool_description(name, tool))
        issues.extend(_check_input_schema(name, tool))

    return issues
