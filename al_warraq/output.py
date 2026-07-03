"""Unified CLI output layer.

Contract (applies to every command):

- Results go to **stdout**; errors, warnings, and notices go to **stderr**.
- ``--json`` prints a single JSON object to stdout with no styling.
- Exit codes: ``0`` success, ``1`` operational failure, ``2`` usage error.
- Errors are a single line plus a ``--help`` hint — never a full help dump.
"""

from __future__ import annotations

import json
import sys
from typing import Any, NoReturn

import typer
from rich.console import Console

from .ncx import NavPoint

console = Console()
err_console = Console(stderr=True)


def fail(message: str, command: str | None = None, *, code: int = 1) -> NoReturn:
    """Print a one-line error (plus a --help hint) to stderr and exit."""
    err_console.print(f"[red]Error:[/red] {message}")
    if command:
        err_console.print(f"[dim]Try 'al-warraq {command} --help' for usage.[/dim]")
    raise typer.Exit(code)


def warn(message: str) -> None:
    """Print a warning line to stderr."""
    err_console.print(f"[yellow]{message}[/yellow]")


def emit_json(payload: dict[str, Any]) -> None:
    """Print a single JSON object to stdout, unstyled."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def emit_data(text: str) -> None:
    """Print raw result data to stdout with no markup or highlighting."""
    sys.stdout.write(text if text.endswith("\n") else text + "\n")


def print_kv(pairs: list[tuple[str, str]]) -> None:
    """Aligned key-value block — the shared human format for record-like results."""
    width = max(len(k) for k, _ in pairs) + 1
    for key, value in pairs:
        console.print(f"[bold]{key + ':':<{width}}[/bold] {value}")


def navpoint_to_dict(pt: NavPoint) -> dict[str, Any]:
    """Serialize a NavPoint subtree for --json output."""
    return {
        "label": pt.label,
        "type": pt.nav_type,
        "file": pt.file,
        "anchor": pt.anchor,
        "children": [navpoint_to_dict(c) for c in pt.children],
    }
