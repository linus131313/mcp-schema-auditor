"""Tests for the schema loader."""

import json
import pytest
from mcp_governance.loader import load_schema_str, SchemaError


def test_load_standard_format():
    schema_json = json.dumps({"tools": [{"name": "foo"}]})
    schema = load_schema_str(schema_json)
    assert schema["tools"][0]["name"] == "foo"


def test_load_bare_array():
    schema_json = json.dumps([{"name": "foo"}])
    schema = load_schema_str(schema_json)
    assert schema["tools"][0]["name"] == "foo"


def test_missing_tools_key_raises():
    with pytest.raises(SchemaError):
        load_schema_str(json.dumps({"something_else": []}))


def test_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        load_schema_str("not json at all {{{")


def test_non_array_tools_raises():
    with pytest.raises(SchemaError):
        load_schema_str(json.dumps({"tools": "not-an-array"}))
