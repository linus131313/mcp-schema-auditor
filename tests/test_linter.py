"""Tests for the schema linter."""

import pytest
from mcp_governance.linter import lint
from mcp_governance.models import Severity
from tests.fixtures import (
    GOOD_SCHEMA,
    MISSING_DESC_SCHEMA,
    MISSING_PARAM_DESC_SCHEMA,
    OVER_BROAD_SCHEMA,
)


def test_good_schema_has_no_errors():
    issues = lint(GOOD_SCHEMA)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], f"Unexpected errors: {errors}"


def test_missing_tool_description_is_error():
    issues = lint(MISSING_DESC_SCHEMA)
    codes = [i.code for i in issues]
    assert "L001" in codes


def test_missing_param_description_is_error():
    issues = lint(MISSING_PARAM_DESC_SCHEMA)
    codes = [i.code for i in issues]
    assert "L020" in codes


def test_over_broad_type_is_warning():
    issues = lint(OVER_BROAD_SCHEMA)
    warnings = [i for i in issues if i.code == "L030"]
    assert warnings, "Expected L030 warning for over-broad object type"
    assert all(w.severity == Severity.WARNING for w in warnings)


def test_duplicate_tool_names():
    schema = {
        "tools": [
            {"name": "foo", "description": "First foo.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "foo", "description": "Second foo.", "inputSchema": {"type": "object", "properties": {}}},
        ]
    }
    issues = lint(schema)
    assert any(i.code == "L005" for i in issues)


def test_single_char_param_name_warns():
    schema = {
        "tools": [
            {
                "name": "transform",
                "description": "Transforms data in some way and returns the result.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "string", "description": "Some value."}
                    },
                },
            }
        ]
    }
    issues = lint(schema)
    assert any(i.code == "L022" for i in issues)


def test_conventional_single_char_ok():
    schema = {
        "tools": [
            {
                "name": "sample",
                "description": "Samples n items from the population with replacement.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "n": {"type": "integer", "description": "Number of items to sample.", "minimum": 1}
                    },
                    "required": ["n"],
                },
            }
        ]
    }
    issues = lint(schema)
    assert not any(i.code == "L022" for i in issues)


def test_numeric_without_bounds_is_info():
    schema = {
        "tools": [
            {
                "name": "paginate",
                "description": "Returns a page of results from the database query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "description": "Page number to fetch."}
                    },
                },
            }
        ]
    }
    issues = lint(schema)
    assert any(i.code == "L031" for i in issues)


def test_empty_tools_list():
    issues = lint({"tools": []})
    assert issues == []
