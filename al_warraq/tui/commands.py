"""Slash commands for the interactive app.

One vocabulary: every slash command maps onto the same Book facade call as
its one-shot CLI verb, and renders with the same builders from ``output.py``.
This module imports nothing from textual, so it is plain-unit-testable.
"""

from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass

import typer
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from ..book import Book
from ..exceptions import AlWarraqError
from ..output import build_kv, build_search_results, build_toc_tree, inspect_pairs

_CONTENT_FORMATS = ("markdown", "plaintext", "html")


@dataclass(frozen=True)
class SlashCommand:
    """One entry in the command popup."""

    name: str
    usage: str
    help: str
    # None marks an app-level command (quit); execute() returns None for it.
    handler: Callable[[Book, list[str]], RenderableType] | None


def _toc(book: Book, _args: list[str]) -> RenderableType:
    return build_toc_tree(book.doc_title, book.toc())


def _search(book: Book, args: list[str]) -> RenderableType:
    query = " ".join(args)
    if not query:
        return _error("Usage: /search <query>")
    hits = book.search(query, limit=10)
    if not hits:
        return Text(f"No matches for {query!r}", style="yellow")
    return build_search_results(query, "section", hits)


def _content(book: Book, args: list[str]) -> RenderableType:
    if not args:
        return _error("Usage: /content <anchor> [markdown|plaintext|html]")
    ref = args[0]
    # Readable text by default: raw HTML is unreadable in a results pane.
    output_format = args[1] if len(args) > 1 else "markdown"
    if output_format not in _CONTENT_FORMATS:
        return _error(f"Format must be one of: {', '.join(_CONTENT_FORMATS)}")
    section = book.section_by_ref(
        ref, output_format=None if output_format == "html" else output_format,
    )
    return Text(section.text)


def _info(book: Book, _args: list[str]) -> RenderableType:
    return build_kv(inspect_pairs(book))


def _open(book: Book, _args: list[str]) -> RenderableType:
    extract_dir = str(book.info.opf_path.parent)
    typer.launch(extract_dir)
    return Text(f"Opened {extract_dir}", style="dim")


def _help(_book: Book, _args: list[str]) -> RenderableType:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    for cmd in COMMANDS:
        table.add_row(Text(cmd.usage, style="bold"), cmd.help)
    table.add_row(Text("<text>", style="bold"), "Search the book (same as /search).")
    return table


COMMANDS: tuple[SlashCommand, ...] = (
    SlashCommand("/toc", "/toc", "Show the table of contents.", _toc),
    SlashCommand("/search", "/search <query>", "Full-text BM25 search.", _search),
    SlashCommand(
        "/content", "/content <anchor> [fmt]",
        "Show one section's content (markdown by default).", _content,
    ),
    SlashCommand("/info", "/info", "Title, version, TOC type, paths.", _info),
    SlashCommand("/open", "/open", "Open the extracted book folder.", _open),
    SlashCommand("/help", "/help", "List all commands.", _help),
    SlashCommand("/quit", "/quit", "Exit the app.", None),
)


def match(prefix: str) -> list[SlashCommand]:
    """Commands whose name starts with ``prefix`` — feeds the popup filter."""
    return [cmd for cmd in COMMANDS if cmd.name.startswith(prefix)]


def execute(book: Book, line: str) -> RenderableType | None:
    """Run one input line and return what to show, or None to quit.

    Bare text searches the book; ``/verb args`` dispatches to its handler.
    Errors come back as a single red line — never an exception.
    """
    line = line.strip()
    if not line.startswith("/"):
        return _search(book, [line])

    try:
        verb, *args = shlex.split(line)
    except ValueError as e:
        return _error(str(e))
    command = next((cmd for cmd in COMMANDS if cmd.name == verb), None)
    if command is None:
        return _error(f"Unknown command: {verb}. Type /help for the list.")
    if command.handler is None:
        return None

    try:
        return command.handler(book, args)
    except AlWarraqError as e:
        return _error(str(e))


def _error(message: str) -> Text:
    """The single red error line, same shape as the CLI output contract."""
    return Text(f"Error: {message}", style="red")
