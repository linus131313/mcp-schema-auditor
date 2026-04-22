"""Tests for the capability scorer."""

from mcp_governance.scorer import score
from tests.fixtures import GOOD_SCHEMA, MISSING_DESC_SCHEMA, DANGEROUS_CAPABILITY_SCHEMA


def test_good_schema_scores_well():
    scores = score(GOOD_SCHEMA)
    assert len(scores) == 1
    assert scores[0].total >= 60, f"Expected score ≥60 for a well-formed tool, got {scores[0].total}"


def test_missing_description_scores_zero_on_desc():
    scores = score(MISSING_DESC_SCHEMA)
    assert len(scores) == 1
    assert scores[0].description_score == 0


def test_dangerous_tool_scores_low_on_security():
    scores = score(DANGEROUS_CAPABILITY_SCHEMA)
    assert len(scores) == 1
    assert scores[0].security_score <= 10


def test_grade_a_for_perfect_tool():
    schema = {
        "tools": [
            {
                "name": "list_files",
                "description": (
                    "Lists all files in the given directory path. Returns a JSON array of filenames. "
                    "Example: list_files('/home/user/docs') returns ['a.txt', 'b.pdf']. "
                    "Raises an error if the directory does not exist."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Absolute path to the directory to list.",
                            "minLength": 1,
                            "pattern": "^/",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum recursion depth (0 = top level only).",
                            "minimum": 0,
                            "maximum": 10,
                        },
                    },
                    "required": ["directory"],
                },
            }
        ]
    }
    scores = score(schema)
    assert scores[0].grade in ("A", "B"), f"Expected A or B grade, got {scores[0].grade} ({scores[0].total}/100)"


def test_empty_schema_returns_no_scores():
    scores = score({"tools": []})
    assert scores == []


def test_score_fields_are_within_bounds():
    scores = score(GOOD_SCHEMA)
    for s in scores:
        assert 0 <= s.description_score <= 30
        assert 0 <= s.parameter_score <= 30
        assert 0 <= s.type_strictness_score <= 20
        assert 0 <= s.security_score <= 20
        assert 0 <= s.total <= 100
