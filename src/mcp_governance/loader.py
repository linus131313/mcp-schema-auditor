"""Load and validate MCP server schema from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaError(ValueError):
    pass


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load an MCP server schema from a JSON file.

    Accepts either the full server manifest format or a bare tools list:
      {"tools": [...]}          ← standard
      [...]                     ← bare array of tool objects
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"tools": data}
    if not isinstance(data, dict):
        raise SchemaError("Schema must be a JSON object or array.")
    if "tools" not in data:
        raise SchemaError('Schema must contain a "tools" key.')
    if not isinstance(data["tools"], list):
        raise SchemaError('"tools" must be a JSON array.')
    return data


def load_schema_str(text: str) -> dict[str, Any]:
    """Load schema from a JSON string (useful for testing)."""
    data = json.loads(text)
    if isinstance(data, list):
        data = {"tools": data}
    if "tools" not in data:
        raise SchemaError('Schema must contain a "tools" key.')
    if not isinstance(data["tools"], list):
        raise SchemaError('"tools" must be a JSON array.')
    return data
