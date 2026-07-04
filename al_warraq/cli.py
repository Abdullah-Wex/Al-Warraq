"""Al-Warraq CLI — thin frontend over the Book facade.

Every command is: parse arguments → one Book call → render.
Business logic lives in ``book.py``; rendering helpers live in ``output.py``.
"""

import os
from pathlib import Path

import typer
from rich.tree import Tree

from . import __version__
from .book import Book
from .epub import extract_epub, hash_epub
from .exceptions import AlWarraqError
from .ncx import NavPoint
from .output import (
    console,
    emit_data,
    emit_json,
    fail,
    navpoint_to_dict,
    print_kv,
    warn,
)
from .storage import resolve_output_dir

_DEBUG = os.environ.get("AL_WARRAQ_DEBUG", "").lower() in ("1", "true")
app = typer.Typer(
    help="Al-Warraq (الورّاق) — lightweight EPUB inspection",
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
    pairs = [
        ("Title", book.title or "(none)"),
        ("Version", f"EPUB {book.version}"),
        ("TOC Type", book.toc_type),
    ]
    if book.info.toc.toc_href:
        pairs.append(("TOC File", book.info.toc.toc_href))
    pairs.append(("OPF Path", str(book.info.opf_path)))
    print_kv(pairs)


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
    _print_toc_tree(book.doc_title, nav_points)


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

    console.print(
        f"[bold]{len(hits)} result(s) for[/bold] {query!r} "
        f"[dim](--group {group})[/dim]\n"
    )
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
        console.print(f"[green]{h.score:6.2f}[/green]  {crumb}{suffix}")
        if loc:
            console.print(f"        [dim]({loc})[/dim]")
        if show_content and h.content:
            console.print(f"[dim]{'─' * 60}[/dim]")
            console.print(h.content, markup=False, highlight=False)
            console.print(f"[dim]{'─' * 60}[/dim]\n")


# ------------------------------------------------------------- toc rendering

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


def _print_toc_tree(title: str, nav_points: list[NavPoint]) -> None:
    """Render the classified TOC as a colored tree."""
    tree = Tree(f"[bold]{title}[/bold]")
    _add_points(tree, nav_points)
    console.print(tree)


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


def cli_entry() -> None:
    """Entry point for pyproject.toml."""
    app()
