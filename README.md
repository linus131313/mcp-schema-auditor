# mcp-governance-toolkit

**CLI + library for auditing MCP server schemas** — lint for quality, flag security risks, and score tool definitions against a structured capability rubric.

MCP (Model Context Protocol) servers expose tools to AI agents. Poor tool descriptions, under-typed parameters, and insecure capability patterns cause agent failures and security vulnerabilities. `mcp-governance` catches these issues before they reach production.

---

## Features

| Command | What it checks |
|---------|----------------|
| `mcp-audit lint` | Missing descriptions, unclear parameter names, over-broad types, duplicate tool names |
| `mcp-audit security` | Prompt-injection patterns in descriptions, dangerous capability signals (shell exec, file write, credential handling), injection-sink parameter names |
| `mcp-audit score` | Composite 0–100 quality score per tool (description, parameters, type strictness, security posture) |
| `mcp-audit audit` | Full audit: all of the above in one pass |

All commands exit `0` on clean pass, `1` on errors, `2` on bad input. JSON output is available with `--json` for CI pipelines.

---

## Install

```bash
pip install mcp-governance
```

Or from source:

```bash
git clone https://github.com/linus131313/mcp-governance-toolkit
cd mcp-governance-toolkit
pip install -e ".[dev]"
```

Requires Python 3.11+.

---

## Usage

### Schema format

Point the tool at a JSON file. Two formats are accepted:

**Standard (MCP server manifest):**
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Reads the contents of a file at the given path.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Absolute path to the file.",
            "minLength": 1
          }
        },
        "required": ["path"]
      }
    }
  ]
}
```

**Bare array (tool list only):**
```json
[{ "name": "read_file", ... }]
```

### Commands

```bash
# Lint for quality issues
mcp-audit lint myserver.json

# Security scan
mcp-audit security myserver.json

# Score each tool (0–100)
mcp-audit score myserver.json

# Full audit in one pass
mcp-audit audit myserver.json

# JSON output for CI
mcp-audit audit myserver.json --json
```

### Example output

```
──────────────── MCP Governance Audit: myserver ────────────────
Tools: 3  |  Score: 71/100 (B)  |  Errors: 1  |  Warnings: 2

Lint Issues
  ERROR     L001  ingest_data  Tool is missing a description.
  WARNING   L030  store_blob   Parameter "data" has over-broad type "object" …

Security Issues
  WARNING   S020  run_query    Parameter "sql" is a common injection sink …

Tool Scores
  read_file                       88/100  A
  store_blob                      64/100  C
  run_query                       60/100  C
```

---

## Lint rules

| Code | Severity | Description |
|------|----------|-------------|
| L001 | ERROR | Tool has no description |
| L002 | WARNING | Tool description is very short (< 20 chars) |
| L003 | INFO | Description starts with a vague verb |
| L005 | ERROR | Duplicate tool name |
| L010 | ERROR | `inputSchema` is not a JSON object |
| L011 | WARNING | `inputSchema.type` is not `"object"` |
| L020 | ERROR | Parameter has no description |
| L021 | WARNING | Parameter description is very short |
| L022 | WARNING | Single-character parameter name (non-conventional) |
| L030 | WARNING | Over-broad type (`object`/`array`) with no refinement |
| L031 | INFO | Numeric parameter has no `minimum`/`maximum` bounds |

## Security rules

| Code | Severity | Description |
|------|----------|-------------|
| S001 | ERROR | Prompt-injection pattern in tool description |
| S010 | ERROR | Shell/exec/eval capability reference |
| S011 | WARNING | File write/delete without scoping |
| S012 | WARNING | Arbitrary network request capability |
| S013 | WARNING | Credential/secret/password reference |
| S020 | WARNING | Injection-sink parameter name (`command`, `sql`, `code`, `script`, …) |

## Scoring rubric

Each tool is scored 0–100 across four dimensions:

| Dimension | Max | Criteria |
|-----------|-----|----------|
| Description quality | 30 | Length, examples, specificity |
| Parameter quality | 30 | All params described; no vague names |
| Type strictness | 20 | Typed + constrained parameters |
| Security posture | 20 | No security findings |

**Grade scale:** A ≥ 90 · B ≥ 75 · C ≥ 60 · D ≥ 40 · F < 40

---

## Library usage

```python
import json
from mcp_governance.loader import load_schema
from mcp_governance.linter import lint
from mcp_governance.security import check_security
from mcp_governance.scorer import score

schema = load_schema("myserver.json")

lint_issues = lint(schema)
security_issues = check_security(schema)
tool_scores = score(schema)

for issue in lint_issues:
    print(issue)

for s in tool_scores:
    print(f"{s.tool}: {s.total}/100 ({s.grade})")
```

---

## Running tests

```bash
pytest
pytest --cov=mcp_governance --cov-report=term-missing
```

---

## Scope and limits

- Works on static schemas (JSON files or in-memory dicts). It does not connect to live MCP servers.
- Security checks are heuristic — they catch common patterns, not all possible vulnerabilities.
- The scoring rubric is opinionated and based on the author's governance research; it is not an official MCP standard.
- No support for YAML schemas yet (convert to JSON first).

---

## Author

**Linus Teklenburg** — [linus-teklenburg.de](https://linus-teklenburg.de) · hey@linus-teklenburg.de

MIT License. See [LICENSE](LICENSE).
