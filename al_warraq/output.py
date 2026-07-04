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
from typing import TYPE_CHECKING, Any, NoReturn

import typer
from rich.console import Console, Group, RenderableType
from rich.markup import escape
from rich.text import Text
from rich.tree import Tree

from .ncx import NavPoint

if TYPE_CHECKING:
    from .book import Book
    from .search import SearchHit

console = Console()
err_console = Console(stderr=True)


def fail(message: str, command: str | None = None, *, code: int = 1) -> NoReturn:
    """Print a one-line error (plus a --help hint) to stderr and exit."""
    err_console.print(f"[red]Error:[/red] {message}")
    if command:
        err_console.print(f"[dim]Try 'al-warraq {command} --help' for usage.[/dim]")
    raise typer.Exit(code)


def warn(message: str) -> None:
    """Print a warning line to stderr. The message is literal, not markup."""
    err_console.print(f"[yellow]{escape(message)}[/yellow]")


def emit_json(payload: dict[str, Any]) -> None:
    """Print a single JSON object to stdout, unstyled."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def emit_data(text: str) -> None:
    """Print raw result data to stdout with no markup or highlighting."""
    sys.stdout.write(text if text.endswith("\n") else text + "\n")


def print_kv(pairs: list[tuple[str, str]]) -> None:
    """Aligned key-value block — the shared human format for record-like results."""
    console.print(build_kv(pairs))


def navpoint_to_dict(pt: NavPoint) -> dict[str, Any]:
    """Serialize a NavPoint subtree for --json output."""
    return {
        "label": pt.label,
        "type": pt.nav_type,
        "file": pt.file,
        "anchor": pt.anchor,
        "children": [navpoint_to_dict(c) for c in pt.children],
    }


# ---------------------------------------------------------- renderable builders
#
# Pure builders: they return Rich renderables and never print. The CLI prints
# them on `console`; the TUI writes the very same objects into its results
# pane, so both frontends share one look.

_TYPE_STYLE = {
    "chapter": "green",
    "part": "bold cyan",
    "front_matter": "dim",
    "back_matter": "dim",
    "section": "blue",
    "subsection": "dim blue",
    "minor": "dim",
}
_TYPE_TAG = {
    "chapter": "CH",
    "part": "PT",
    "front_matter": "FM",
    "back_matter": "BM",
    "section": "S1",
    "subsection": "S2",
    "minor": "S3",
}


def inspect_pairs(book: Book) -> list[tuple[str, str]]:
    """The key-value pairs shown by ``inspect`` (and the TUI's ``/info``)."""
    pairs = [
        ("Title", book.title or "(none)"),
        ("Version", f"EPUB {book.version}"),
        ("TOC Type", book.toc_type),
    ]
    if book.info.toc.toc_href:
        pairs.append(("TOC File", book.info.toc.toc_href))
    pairs.append(("OPF Path", str(book.info.opf_path)))
    return pairs


def build_kv(pairs: list[tuple[str, str]]) -> Text:
    """Aligned key-value block as one renderable."""
    width = max(len(k) for k, _ in pairs) + 1
    lines = [
        f"[bold]{key + ':':<{width}}[/bold] {value}" for key, value in pairs
    ]
    return Text.from_markup("\n".join(lines))


def build_toc_tree(title: str, nav_points: list[NavPoint]) -> Tree:
    """The classified TOC as a colored tree."""
    tree = Tree(f"[bold]{title}[/bold]")
    _add_points(tree, nav_points)
    return tree


def _add_points(parent: Tree, points: list[NavPoint]) -> None:
    for pt in points:
        nav_type = pt.nav_type or "section"
        style = _TYPE_STYLE.get(nav_type, "")
        tag = _TYPE_TAG.get(nav_type, "")
        loc_parts = []
        if pt.file:
            loc_parts.append(pt.file)
        if pt.anchor:
            loc_parts.append(f"#{pt.anchor}")
        src = " · ".join(loc_parts)
        loc_str = f"  [dim]({src})[/dim]" if src else ""
        tag_str = f"[{style}]\\[{tag}][/{style}] " if tag else ""
        label_str = f"[{style}]{pt.label}[/{style}]" if style else pt.label
        branch = parent.add(f"{tag_str}{label_str}{loc_str}")
        _add_points(branch, pt.children)


def build_search_results(
    query: str,
    group: str,
    hits: list[SearchHit],
    *,
    show_content: bool = False,
) -> RenderableType:
    """Ranked search hits as one renderable (header line + one block per hit)."""
    parts: list[RenderableType] = [
        Text.from_markup(
            f"[bold]{len(hits)} result(s) for[/bold] {query!r} "
            f"[dim](--group {group})[/dim]\n"
        ),
    ]
    for h in hits:
        crumb = " › ".join(h.breadcrumb)  # noqa: RUF001
        loc_parts = []
        if h.file:
            loc_parts.append(h.file)
        if h.anchor:
            loc_parts.append(f"#{h.anchor}")
        loc = " · ".join(loc_parts)
        suffix = (
            f" [dim]({h.n_sections} matching section(s))[/dim]"
            if group == "chapter" and h.n_sections > 1 else ""
        )
        parts.append(
            Text.from_markup(f"[green]{h.score:6.2f}[/green]  {crumb}{suffix}")
        )
        if loc:
            parts.append(Text.from_markup(f"        [dim]({loc})[/dim]"))
        if show_content and h.content:
            rule = Text("─" * 60, style="dim")
            parts.extend([rule, Text(h.content), rule, Text()])
    return Group(*parts)
