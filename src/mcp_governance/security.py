"""Security checks for MCP tool schemas."""

from __future__ import annotations

import re
from typing import Any

from .models import SecurityIssue, Severity

# Patterns in tool descriptions that could be repurposed for prompt injection
_INJECTION_PATTERNS = [
    (
        re.compile(r"\bignore (previous|all|above|prior)\b", re.IGNORECASE),
        "S001",
        "Description contains 'ignore previous/all/above' — classic prompt-injection phrasing.",
    ),
    (
        re.compile(r"\bforget (everything|all|previous)\b", re.IGNORECASE),
        "S001",
        "Description contains 'forget everything/all/previous' — prompt-injection pattern.",
    ),
    (
        re.compile(r"\byou are now\b", re.IGNORECASE),
        "S001",
        "Description contains 'you are now' — persona-override injection pattern.",
    ),
    (
        re.compile(r"\bact as\b.{0,20}\b(admin|root|superuser|god|assistant)\b", re.IGNORECASE),
        "S001",
        "Description contains role-escalation phrasing ('act as admin/root/...').",
    ),
]

# Capability keywords that warrant a warning about broad access
_DANGEROUS_CAPABILITIES = [
    (
        re.compile(r"\b(exec(ute)?|eval|shell|subprocess|os\.system)\b", re.IGNORECASE),
        "S010",
        Severity.ERROR,
        "Tool description references shell/exec/eval — arbitrary code execution risk.",
    ),
    (
        re.compile(r"\b(write|delete|overwrite|remove|rm -rf)\b.{0,40}\bfile\b", re.IGNORECASE),
        "S011",
        Severity.WARNING,
        "Tool description references file write/delete — ensure path scoping is enforced.",
    ),
    (
        re.compile(r"\b(network|http|fetch|curl|request)\b.{0,40}\b(any|all|arbitrary)\b", re.IGNORECASE),
        "S012",
        Severity.WARNING,
        "Tool appears to allow arbitrary network requests — consider allowlisting destinations.",
    ),
    (
        re.compile(r"\b(password|secret|credential|api.?key|token)\b", re.IGNORECASE),
        "S013",
        Severity.WARNING,
        "Tool description mentions credentials/secrets — verify these are not logged or leaked.",
    ),
]

# Overly permissive parameter patterns
_PERMISSIVE_PARAM_NAMES = re.compile(
    r"^(command|cmd|code|script|query|sql|expression|eval|exec)$", re.IGNORECASE
)


def _check_description_for_injection(
    tool_name: str, desc: str
) -> list[SecurityIssue]:
    issues: list[SecurityIssue] = []
    for pattern, code, message in _INJECTION_PATTERNS:
        if pattern.search(desc):
            issues.append(
                SecurityIssue(
                    tool=tool_name,
                    severity=Severity.ERROR,
                    code=code,
                    message=message,
                    detail=f"Matched in description: {desc[:120]}",
                )
            )
    return issues


def _check_description_for_capabilities(
    tool_name: str, desc: str
) -> list[SecurityIssue]:
    issues: list[SecurityIssue] = []
    for pattern, code, severity, message in _DANGEROUS_CAPABILITIES:
        if pattern.search(desc):
            issues.append(
                SecurityIssue(
                    tool=tool_name,
                    severity=severity,
                    code=code,
                    message=message,
                )
            )
    return issues


def _check_parameters_for_injection_sinks(
    tool_name: str, schema: dict[str, Any]
) -> list[SecurityIssue]:
    issues: list[SecurityIssue] = []
    properties = schema.get("inputSchema", {}).get("properties", {})
    if not isinstance(properties, dict):
        return issues

    for param_name in properties:
        if _PERMISSIVE_PARAM_NAMES.match(param_name):
            issues.append(
                SecurityIssue(
                    tool=tool_name,
                    severity=Severity.WARNING,
                    code="S020",
                    message=(
                        f'Parameter "{param_name}" is a common injection sink '
                        "(command/code/script/sql). Ensure input is sanitised before use."
                    ),
                )
            )
    return issues


def check_security(schema: dict[str, Any]) -> list[SecurityIssue]:
    """Run all security checks on an MCP schema; return a list of issues."""
    issues: list[SecurityIssue] = []
    for tool in schema.get("tools", []):
        if not isinstance(tool, dict):
            continue
        name = tool.get("name", "<unnamed>")
        desc = tool.get("description", "")
        issues.extend(_check_description_for_injection(name, desc))
        issues.extend(_check_description_for_capabilities(name, desc))
        issues.extend(_check_parameters_for_injection_sinks(name, tool))
    return issues
