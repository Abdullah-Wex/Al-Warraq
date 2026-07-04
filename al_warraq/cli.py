"""Al-Warraq CLI — thin frontend over the Book facade.

Every command is: parse arguments → one Book call → render.
Business logic lives in ``book.py``; rendering helpers live in ``output.py``.
"""

import importlib.util
import os
import sys
from pathlib import Path

import typer

from . import __version__
from .book import Book
from .epub import extract_epub, hash_epub
from .exceptions import AlWarraqError
from .output import (
    build_search_results,
    build_toc_tree,
    console,
    emit_data,
    emit_json,
    fail,
    inspect_pairs,
    navpoint_to_dict,
    print_kv,
    warn,
)
from .storage import resolve_output_dir

_DEBUG = os.environ.get("AL_WARRAQ_DEBUG", "").lower() in ("1", "true")
app = typer.Typer(
    help=(
        "Al-Warraq (الورّاق) — lightweight EPUB inspection\n\n"
        "al-warraq BOOK.epub opens the interactive browser "
        "(requires the [tui] extra)."
    ),
    pretty_exceptions_enable=_DEBUG,
)
_DEFAULT_OUT = resolve_output_dir()

_PATH_ARG = typer.Argument(None, help="Path to EPUB file.")
_OUT_OPT = typer.Option(
    _DEFAULT_OUT, "--output-dir", "-o", help="Extraction directory.",
)
_JSON_OPT = typer.Option(
    False, "--json", help="Print a single JSON object to stdout.",
)


def _require_path(ctx: typer.Context, path: Path | None) -> Path:
    """Validate that path was provided; one-line error otherwise."""
    if path is None:
        fail("Missing required argument: PATH", ctx.command.name, code=2)
    return path


def _open_book(path: Path, output_dir: str, command: str) -> Book:
    """Open the book, translating library errors into CLI failures."""
    try:
        return Book.open(path, output_dir)
    except AlWarraqError as e:
        fail(str(e), command)
    except Exception as e:
        fail(f"Unexpected error: {e}", command)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"al-warraq {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, is_eager=True,
        help="Show version.",
    ),
) -> None:
    """Al-Warraq (الورّاق) — lightweight EPUB inspection."""


@app.command()
def inspect(
    ctx: typer.Context,
    path: Path | None = _PATH_ARG,
    output_dir: str = _OUT_OPT,
    as_json: bool = _JSON_OPT,
) -> None:
    """Inspect an EPUB: version, TOC type, title."""
    epub_path = _require_path(ctx, path)
    book = _open_book(epub_path, output_dir, "inspect")

    if as_json:
        emit_json({
            "title": book.title,
            "version": book.version,
            "toc": {"type": book.toc_type, "href": book.info.toc.toc_href},
            "opf_path": str(book.info.opf_path),
            "hash": book.hash,
        })
        return
    print_kv(inspect_pairs(book))


@app.command()
def extract(
    ctx: typer.Context,
    path: Path | None = _PATH_ARG,
    output_dir: str = _OUT_OPT,
    as_json: bool = _JSON_OPT,
) -> None:
    """Extract an EPUB to a directory."""
    epub_path = _require_path(ctx, path)
    try:
        extract_dir = extract_epub(str(epub_path), output_dir)
    except AlWarraqError as e:
        fail(str(e), "extract")
    except Exception as e:
        fail(f"Unexpected error: {e}", "extract")

    if as_json:
        emit_json({
            "extract_dir": str(extract_dir),
            "hash": hash_epub(str(epub_path)),
        })
        return
    print_kv([("Extracted to", str(extract_dir))])


@app.command()
def validate(
    ctx: typer.Context,
    path: Path | None = _PATH_ARG,
    as_json: bool = _JSON_OPT,
) -> None:
    """Validate an EPUB file (valid zip, has OPF, has TOC)."""
    epub_path = _require_path(ctx, path)
    try:
        book = Book.open(epub_path, _DEFAULT_OUT)
    except AlWarraqError as e:
        if as_json:
            emit_json({"valid": False, "error": str(e)})
            raise typer.Exit(1) from None
        fail(f"Invalid: {e}", "validate")
    except Exception as e:
        fail(f"Unexpected error: {e}", "validate")

    if as_json:
        emit_json({
            "valid": True,
            "version": book.version,
            "toc": {"type": book.toc_type, "href": book.info.toc.toc_href},
        })
        return
    console.print(f"[green]Valid EPUB {book.version}[/green]")
    if book.toc_type != "unknown":
        console.print(f"  TOC: {book.toc_type} ({book.info.toc.toc_href})")
    else:
        console.print("  [yellow]TOC: not found[/yellow]")


@app.command()
def toc(
    ctx: typer.Context,
    path: Path | None = _PATH_ARG,
    output_dir: str = _OUT_OPT,
    as_json: bool = _JSON_OPT,
) -> None:
    """Display table of contents as a tree."""
    epub_path = _require_path(ctx, path)
    book = _open_book(epub_path, output_dir, "toc")

    try:
        nav_points = book.toc()
    except AlWarraqError as e:
        fail(str(e), "toc")

    if as_json:
        emit_json({
            "doc_title": book.doc_title,
            "nav_points": [navpoint_to_dict(pt) for pt in nav_points],
        })
        return
    console.print(build_toc_tree(book.doc_title, nav_points))


@app.command()
def content(
    ctx: typer.Context,
    path: Path | None = _PATH_ARG,
    anchor: str | None = typer.Option(None, "--anchor", "-a", help="TOC anchor ID."),
    file: str | None = typer.Option(
        None, "--file", "-f", help="Chapter file path (relative to EPUB).",
    ),
    exclude: str | None = typer.Option(
        None, "--exclude", "-x", help="Comma-separated anchor IDs to exclude.",
    ),
    parse_to: str | None = typer.Option(
        None, "--parse-to", "-p", help="Output format: plaintext, markdown.",
    ),
    output_dir: str = _OUT_OPT,
    as_json: bool = _JSON_OPT,
) -> None:
    """Extract content for a TOC section by anchor or file."""
    epub_path = _require_path(ctx, path)
    if anchor is None and file is None:
        fail("Provide --anchor or --file", "content", code=2)

    book = _open_book(epub_path, output_dir, "content")
    exclude_list = [a.strip() for a in exclude.split(",")] if exclude else None

    try:
        section = book.section(
            anchor=anchor, file=file,
            output_format=parse_to, exclude=exclude_list,
        )
    except AlWarraqError as e:
        fail(str(e), "content")

    if as_json:
        emit_json({
            "file": section.file,
            "anchor": section.anchor,
            "format": section.output_format,
            "content": section.text,
        })
    else:
        emit_data(section.text)


@app.command()
def search(
    ctx: typer.Context,
    path: Path | None = _PATH_ARG,
    query: str | None = typer.Argument(None, help="Search query."),
    group: str = typer.Option(
        "section", "--group", "-g",
        help="Result grouping: section, chapter, or flat.",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results."),
    show_content: bool = typer.Option(
        False, "--show-content", help="Print each result's section body.",
    ),
    fmt: str | None = typer.Option(
        None, "--format", "-f",
        help="Content format (with --show-content): html, plaintext, markdown.",
    ),
    output_dir: str = typer.Option(
        _DEFAULT_OUT, "--output-dir", "-o", help="Extraction/index directory.",
    ),
    as_json: bool = _JSON_OPT,
) -> None:
    """Full-text BM25 search across an EPUB's sections."""
    epub_path = _require_path(ctx, path)
    if query is None:
        fail("Missing required argument: QUERY", "search", code=2)
    if group not in ("section", "chapter", "flat"):
        fail("--group must be section, chapter, or flat", "search", code=2)
    if fmt is not None and not show_content:
        fail("--format requires --show-content", "search", code=2)
    if fmt is not None and fmt not in ("html", "plaintext", "markdown"):
        fail("--format must be html, plaintext, or markdown", "search", code=2)

    book = _open_book(epub_path, output_dir, "search")
    try:
        hits = book.search(
            query, group=group, limit=limit,
            with_content=show_content, content_format=fmt or "html",
        )
    except AlWarraqError as e:
        fail(str(e), "search")
    except Exception as e:
        fail(f"Unexpected error: {e}", "search")

    if as_json:
        emit_json({
            "query": query,
            "group": group,
            "total": len(hits),
            "results": [
                {
                    "score": round(h.score, 4),
                    "breadcrumb": list(h.breadcrumb),
                    "file": h.file,
                    "anchor": h.anchor,
                    **({"content": h.content} if show_content and h.content else {}),
                }
                for h in hits
            ],
        })
        return

    if not hits:
        warn(f"No matches for {query!r}")
        return

    console.print(build_search_results(query, group, hits, show_content=show_content))


# ----------------------------------------------------------------- invocation
#
# Two ways in, one vocabulary:
#
#   al-warraq <verb> book.epub   → one-shot answer, prints and exits
#   al-warraq book.epub          → interactive browser (the TUI)
#   al-warraq                    → help (never auto-enters the TUI)

_COMMANDS = frozenset({"inspect", "extract", "validate", "toc", "content", "search"})


def _resolve_invocation(args: list[str]) -> Path | None:
    """Return the EPUB path for a path-only invocation, else None.

    Path mode is exactly one positional argument that is not an option, not a
    command name, and either ends in ``.epub`` or is an existing file. Anything
    else (verbs, flags, multiple arguments) is handled by Typer as usual.
    """
    if len(args) != 1:
        return None
    arg = args[0]
    if arg.startswith("-") or arg in _COMMANDS:
        return None
    if arg.endswith(".epub") or Path(arg).is_file():
        return Path(arg)
    return None


def _run_path_mode(path: Path) -> None:
    """Open the interactive browser on ``path``, or fall back to ``inspect``.

    Fallback order: no TTY (scripts/pipes must never block) → tui extra not
    installed (hint on stderr, inspect on stdout) → invalid EPUB (normal
    one-line error, exit 1) → launch the app.
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        app(["inspect", str(path)])
        return
    if importlib.util.find_spec("textual") is None:
        warn("Interactive mode needs the tui extra: pip install al-warraq[tui]")
        app(["inspect", str(path)])
        return

    book = _open_book(path, _DEFAULT_OUT, "inspect")
    from .tui import run_app

    run_app(book)


def cli_entry() -> None:
    """Entry point for pyproject.toml."""
    path = _resolve_invocation(sys.argv[1:])
    if path is None:
        app()
        return
    try:
        _run_path_mode(path)
    except typer.Exit as e:
        # Path mode runs outside the Typer app, so convert its exit signal.
        raise SystemExit(e.exit_code) from None
