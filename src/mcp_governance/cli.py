"""CLI entry point for mcp-governance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from . import __version__
from .loader import load_schema, SchemaError
from .linter import lint
from .models import AuditReport, Severity
from .scorer import score
from .security import check_security

console = Console()
err_console = Console(stderr=True)


def _severity_style(s: Severity) -> str:
    return {"error": "bold red", "warning": "yellow", "info": "cyan"}[s.value]


@click.group()
@click.version_option(__version__, "-V", "--version")
def cli() -> None:
    """mcp-governance: audit MCP server schemas for quality, security, and compliance."""


@cli.command()
@click.argument("schema_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def lint_cmd(schema_file: str, as_json: bool) -> None:
    """Lint an MCP schema for quality issues."""
    try:
        schema = load_schema(schema_file)
    except (SchemaError, json.JSONDecodeError) as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(2)

    issues = lint(schema)

    if as_json:
        click.echo(json.dumps([i.model_dump() for i in issues], indent=2))
        sys.exit(1 if any(i.severity == Severity.ERROR for i in issues) else 0)

    if not issues:
        console.print("[bold green]✓ No lint issues found.[/bold green]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Severity", style="bold", width=9)
    table.add_column("Code", width=6)
    table.add_column("Tool", style="dim")
    table.add_column("Field")
    table.add_column("Message")

    for issue in sorted(issues, key=lambda x: (x.severity.value, x.tool)):
        table.add_row(
            f"[{_severity_style(issue.severity)}]{issue.severity.value.upper()}[/{_severity_style(issue.severity)}]",
            issue.code,
            issue.tool,
            issue.field,
            issue.message,
        )

    console.print(table)

    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    console.print(f"[bold]{errors} error(s), {warnings} warning(s)[/bold]")

    if errors:
        sys.exit(1)


@cli.command()
@click.argument("schema_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def security_cmd(schema_file: str, as_json: bool) -> None:
    """Run security checks on an MCP schema."""
    try:
        schema = load_schema(schema_file)
    except (SchemaError, json.JSONDecodeError) as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(2)

    issues = check_security(schema)

    if as_json:
        click.echo(json.dumps([i.model_dump() for i in issues], indent=2))
        sys.exit(1 if any(i.severity == Severity.ERROR for i in issues) else 0)

    if not issues:
        console.print("[bold green]✓ No security issues found.[/bold green]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Severity", width=9)
    table.add_column("Code", width=6)
    table.add_column("Tool", style="dim")
    table.add_column("Message")

    for issue in sorted(issues, key=lambda x: (x.severity.value, x.tool)):
        table.add_row(
            f"[{_severity_style(issue.severity)}]{issue.severity.value.upper()}[/{_severity_style(issue.severity)}]",
            issue.code,
            issue.tool,
            issue.message,
        )

    console.print(table)
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    console.print(f"[bold]{errors} error(s), {warnings} warning(s)[/bold]")

    if errors:
        sys.exit(1)


@cli.command()
@click.argument("schema_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def score_cmd(schema_file: str, as_json: bool) -> None:
    """Score each tool in an MCP schema (0–100)."""
    try:
        schema = load_schema(schema_file)
    except (SchemaError, json.JSONDecodeError) as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(2)

    tool_scores = score(schema)

    if as_json:
        click.echo(json.dumps([s.model_dump() | {"total": s.total, "grade": s.grade} for s in tool_scores], indent=2))
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Tool", style="dim")
    table.add_column("Desc", justify="right", width=6)
    table.add_column("Params", justify="right", width=7)
    table.add_column("Types", justify="right", width=6)
    table.add_column("Sec", justify="right", width=5)
    table.add_column("Total", justify="right", width=6)
    table.add_column("Grade", justify="center", width=6)

    for s in tool_scores:
        grade_style = {"A": "green", "B": "cyan", "C": "yellow", "D": "orange1", "F": "red"}.get(s.grade, "")
        table.add_row(
            s.tool,
            str(s.description_score),
            str(s.parameter_score),
            str(s.type_strictness_score),
            str(s.security_score),
            str(s.total),
            f"[{grade_style}]{s.grade}[/{grade_style}]",
        )

    console.print(table)

    if tool_scores:
        overall = round(sum(s.total for s in tool_scores) / len(tool_scores))
        console.print(f"[bold]Overall score: {overall}/100[/bold]")


@cli.command()
@click.argument("schema_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def audit(schema_file: str, as_json: bool) -> None:
    """Full audit: lint + security + score."""
    try:
        schema = load_schema(schema_file)
    except (SchemaError, json.JSONDecodeError) as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(2)

    server_name = Path(schema_file).stem
    lint_issues = lint(schema)
    security_issues = check_security(schema)
    tool_scores = score(schema)

    report = AuditReport(
        server_name=server_name,
        tool_count=len(schema.get("tools", [])),
        lint_issues=lint_issues,
        security_issues=security_issues,
        tool_scores=tool_scores,
    )

    if as_json:
        click.echo(
            json.dumps(
                {
                    "server_name": report.server_name,
                    "tool_count": report.tool_count,
                    "overall_score": report.overall_score,
                    "overall_grade": report.overall_grade,
                    "errors": report.error_count,
                    "warnings": report.warning_count,
                    "lint_issues": [i.model_dump() for i in lint_issues],
                    "security_issues": [i.model_dump() for i in security_issues],
                    "tool_scores": [
                        s.model_dump() | {"total": s.total, "grade": s.grade}
                        for s in tool_scores
                    ],
                },
                indent=2,
            )
        )
        sys.exit(1 if report.error_count > 0 else 0)

    console.rule(f"[bold]MCP Governance Audit: {server_name}[/bold]")
    console.print(f"Tools: {report.tool_count}  |  Score: {report.overall_score}/100 ({report.overall_grade})  |  Errors: {report.error_count}  |  Warnings: {report.warning_count}\n")

    if lint_issues:
        console.print("[bold underline]Lint Issues[/bold underline]")
        for issue in sorted(lint_issues, key=lambda x: (x.severity.value, x.tool)):
            sty = _severity_style(issue.severity)
            console.print(f"  [{sty}]{issue.severity.value.upper():8}[/{sty}]  {issue.code}  {issue.tool}  {issue.message}")
        console.print()

    if security_issues:
        console.print("[bold underline]Security Issues[/bold underline]")
        for issue in sorted(security_issues, key=lambda x: (x.severity.value, x.tool)):
            sty = _severity_style(issue.severity)
            console.print(f"  [{sty}]{issue.severity.value.upper():8}[/{sty}]  {issue.code}  {issue.tool}  {issue.message}")
        console.print()

    console.print("[bold underline]Tool Scores[/bold underline]")
    for s in tool_scores:
        grade_style = {"A": "green", "B": "cyan", "C": "yellow", "D": "orange1", "F": "red"}.get(s.grade, "")
        console.print(f"  {s.tool:<30} {s.total:>3}/100  [{grade_style}]{s.grade}[/{grade_style}]")

    sys.exit(1 if report.error_count > 0 else 0)


# Rename commands to match CLI spec
cli.add_command(lint_cmd, name="lint")
cli.add_command(security_cmd, name="security")
cli.add_command(score_cmd, name="score")


def main() -> None:
    cli()
