"""Al-Warraq CLI — inspect EPUB files."""

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.tree import Tree

from . import __version__, inspect_epub
from .classify import (
    classify_children,
    classify_navpoint,
    merge_same_file_runs,
    refine_positional,
    refine_structural,
)
from .content import extract_content
from .epub import extract_epub, find_opf
from .exceptions import InvalidEpubError
from .nav import parse_nav
from .ncx import NavPoint, parse_ncx
from .opf import parse_opf
from .search import search as run_search
from .storage import resolve_output_dir

_DEBUG = os.environ.get("AL_WARRAQ_DEBUG", "").lower() in ("1", "true")
app = typer.Typer(
    help="Al-Warraq (الورّاق) — lightweight EPUB inspection",
    pretty_exceptions_enable=_DEBUG,
)
console = Console()

_DEFAULT_OUT = resolve_output_dir()


def _require_path(ctx: typer.Context, path: Path | None) -> Path:
    """Validate that path was provided. Show help and exit if not."""
    if path is None:
        console.print("[red]Error:[/red] Missing required argument: PATH\n")
        console.print(ctx.get_help())
        raise typer.Exit(1)
    return path


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
    path: Path | None = typer.Argument(None, help="Path to EPUB file."),
    output_dir: str = typer.Option(
        _DEFAULT_OUT, "--output-dir", "-o", help="Extraction directory.",
    ),
) -> None:
    """Inspect an EPUB: version, TOC type, title."""
    epub_path = _require_path(ctx, path)
    try:
        info = inspect_epub(str(epub_path), output_dir)
    except InvalidEpubError as e:
        console.print(f"[red]Error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None

    console.print(f"[bold]Title:[/bold]    {info.title or '(none)'}")
    console.print(f"[bold]Version:[/bold]  EPUB {info.version}")
    console.print(f"[bold]TOC Type:[/bold] {info.toc.toc_type}")
    if info.toc.toc_href:
        console.print(f"[bold]TOC File:[/bold] {info.toc.toc_href}")
    console.print(f"[bold]OPF Path:[/bold] {info.opf_path}")


@app.command()
def extract(
    ctx: typer.Context,
    path: Path | None = typer.Argument(None, help="Path to EPUB file."),
    output_dir: str = typer.Option(
        _DEFAULT_OUT, "--output-dir", "-o", help="Extraction directory.",
    ),
) -> None:
    """Extract an EPUB to a directory."""
    epub_path = _require_path(ctx, path)
    try:
        extract_dir = extract_epub(str(epub_path), output_dir)
    except InvalidEpubError as e:
        console.print(f"[red]Error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None

    console.print(f"Extracted to: {extract_dir}")


@app.command()
def validate(
    ctx: typer.Context,
    path: Path | None = typer.Argument(None, help="Path to EPUB file."),
) -> None:
    """Validate an EPUB file (valid zip, has OPF, has TOC)."""
    epub_path = _require_path(ctx, path)
    try:
        extract_dir = extract_epub(str(epub_path), _DEFAULT_OUT)
        opf_path = find_opf(str(extract_dir))
        info = parse_opf(str(opf_path), str(extract_dir))
    except InvalidEpubError as e:
        console.print(f"[red]Invalid:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None

    console.print(f"[green]Valid EPUB {info.version}[/green]")
    if info.toc.toc_type != "unknown":
        console.print(f"  TOC: {info.toc.toc_type} ({info.toc.toc_href})")
    else:
        console.print("  [yellow]TOC: not found[/yellow]")


@app.command()
def toc(
    ctx: typer.Context,
    path: Path | None = typer.Argument(None, help="Path to EPUB file."),
    output_dir: str = typer.Option(
        _DEFAULT_OUT, "--output-dir", "-o", help="Extraction directory.",
    ),
) -> None:
    """Display table of contents as a tree."""
    epub_path = _require_path(ctx, path)
    try:
        info = inspect_epub(str(epub_path), output_dir)
    except InvalidEpubError as e:
        console.print(f"[red]Error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None

    if info.toc.ncx_path:
        ncx = parse_ncx(str(info.toc.ncx_path))
        title = ncx.doc_title or info.title or "(untitled)"
        nav_points = ncx.nav_points
    elif info.toc.toc_path:
        nav_points = parse_nav(str(info.toc.toc_path))
        title = info.title or "(untitled)"
    else:
        console.print("[yellow]No table of contents found.[/yellow]")
        raise typer.Exit(1)

    # Collapse Packt-style split chapter pairs before classification
    nav_points = merge_same_file_runs(nav_points)

    # Classify top-level points, then refine with positional and
    # structural passes before walking children.
    for pt in nav_points:
        pt.nav_type = classify_navpoint(pt)
    refine_structural(nav_points)
    refine_positional(nav_points)
    classify_children(nav_points)

    # Group chapters under parts (flat TOC only)
    grouped = _group_under_parts(nav_points)
    tree = Tree(f"[bold]{title}[/bold]")

    type_style = {
        "chapter": "green",
        "part": "bold cyan",
        "front_matter": "dim",
        "back_matter": "dim",
        "section": "blue",
        "subsection": "dim blue",
        "minor": "dim",
    }
    type_tag = {
        "chapter": "CH",
        "part": "PT",
        "front_matter": "FM",
        "back_matter": "BM",
        "section": "S1",
        "subsection": "S2",
        "minor": "S3",
    }

    def _add_points(parent: Tree, points: list[NavPoint]) -> None:
        for pt in points:
            nav_type = pt.nav_type or "section"
            style = type_style.get(nav_type, "")
            tag = type_tag.get(nav_type, "")
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

    _add_points(tree, grouped)
    console.print(tree)


@app.command()
def content(
    ctx: typer.Context,
    path: Path | None = typer.Argument(None, help="Path to EPUB file."),
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
    output_dir: str = typer.Option(
        _DEFAULT_OUT, "--output-dir", "-o", help="Extraction directory.",
    ),
) -> None:
    """Extract content for a TOC section by anchor or file."""
    epub_path = _require_path(ctx, path)
    if anchor is None and file is None:
        console.print("[red]Error:[/red] Provide --anchor or --file\n")
        console.print(ctx.get_help())
        raise typer.Exit(1)

    try:
        info = inspect_epub(str(epub_path), output_dir)
    except InvalidEpubError as e:
        console.print(f"[red]Error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None

    # Parse TOC to get all NavPoints
    nav_points = _get_nav_points(info)
    if nav_points is None:
        console.print("[yellow]No table of contents found.[/yellow]")
        raise typer.Exit(1)

    # Flatten all navpoints
    all_points = _flatten_navpoints(nav_points)

    # Resolve the target file
    opf_dir = info.opf_path.parent
    target_pt: NavPoint | None = None

    if file is not None:
        # Resolve file — try exact match, then match by filename
        resolved = _resolve_toc_file(file, all_points)
        if resolved is None:
            console.print(
                f"[red]Error:[/red] File '{file}' not found in TOC",
            )
            raise typer.Exit(1)
        target_file = resolved
        target_anchor: str | None = anchor
        if anchor is not None:
            target_pt = next(
                (pt for pt in all_points
                 if pt.file == target_file and pt.anchor == anchor),
                None,
            )
        else:
            target_pt = next(
                (pt for pt in all_points
                 if pt.file == target_file and pt.anchor is None),
                None,
            )
        child_anchors = (
            _collect_child_anchors(target_pt) if target_pt else []
        )
    elif anchor is not None:
        # Find NavPoint matching anchor
        target_pt = next(
            (pt for pt in all_points if pt.anchor == anchor), None,
        )
        if target_pt is None:
            console.print(
                f"[red]Error:[/red] Anchor '{anchor}' not found in TOC",
            )
            raise typer.Exit(1)
        target_file = target_pt.file
        target_anchor = anchor
        child_anchors = _collect_child_anchors(target_pt)

    # Resolve to absolute path — prefer NavPoint.abs_file when available
    if target_pt is not None and target_pt.abs_file:
        html_path = Path(target_pt.abs_file)
    else:
        html_path = (opf_dir / target_file).resolve()
    if not html_path.exists():
        console.print(f"[red]Error:[/red] File not found: {html_path}")
        raise typer.Exit(1)

    # Collect all TOC anchors for this file
    toc_anchors = [
        pt.anchor for pt in all_points
        if pt.file == target_file and pt.anchor is not None
    ]

    # Derive stop_anchors from the TOC tree so mid-prose anchors (e.g. Packt
    # ``_idParaDest-*`` cross-references) do not truncate section extraction.
    stop_anchors = (
        _stop_anchors_for(target_pt, nav_points) if target_pt else None
    )

    # Parse exclude list
    exclude_list = (
        [a.strip() for a in exclude.split(",")] if exclude else None
    )

    try:
        html = extract_content(
            str(html_path), target_anchor, toc_anchors,
            child_anchors, exclude_list, output_format=parse_to,
            stop_anchors=stop_anchors,
        )
    except InvalidEpubError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    console.print(html, highlight=False)


def _get_nav_points(info: object) -> list[NavPoint] | None:
    """Get NavPoints from NCX or NAV."""
    toc = info.toc  # type: ignore[attr-defined]
    if toc.ncx_path:
        ncx = parse_ncx(str(toc.ncx_path))
        return ncx.nav_points
    if toc.toc_path:
        return parse_nav(str(toc.toc_path))
    return None


def _resolve_toc_file(
    file_input: str, all_points: list[NavPoint],
) -> str | None:
    """Resolve a file input to the full TOC file path.

    Tries exact match first, then matches by filename only.
    """
    # Exact match
    for pt in all_points:
        if pt.file == file_input:
            return pt.file
    # Match by filename (without directory)
    for pt in all_points:
        if pt.file.rsplit("/", 1)[-1] == file_input:
            return pt.file
    # Match by filename (without directory, input might have path)
    input_name = file_input.rsplit("/", 1)[-1]
    for pt in all_points:
        if pt.file.rsplit("/", 1)[-1] == input_name:
            return pt.file
    return None


def _collect_child_anchors(pt: NavPoint) -> list[str]:
    """Collect all descendant anchor IDs from a NavPoint."""
    anchors: list[str] = []
    for child in pt.children:
        if child.anchor:
            anchors.append(child.anchor)
        anchors.extend(_collect_child_anchors(child))
    return anchors


def _stop_anchors_for(
    target: NavPoint, roots: list[NavPoint],
) -> list[str] | None:
    """Derive boundary anchors for ``target`` from the TOC tree.

    Returns the anchors of every TOC sibling that follows ``target`` (and
    their descendants) at each level of the ancestry chain, filtered to
    ``target.file``. Filtering by file is essential because some publishers
    (e.g. Manning) restart paragraph numbering per chapter so anchor IDs
    collide across files — without the filter, a following chapter's anchor
    would coincidentally match an ID in the current chapter and truncate.
    """
    path = _find_path(target, roots)
    if path is None:
        return None
    stops: list[str] = []
    for depth, node in enumerate(path):
        siblings = roots if depth == 0 else path[depth - 1].children
        idx = siblings.index(node)
        for sib in siblings[idx + 1 :]:
            _collect_same_file_anchors(sib, target.file, stops)
    return stops


def _collect_same_file_anchors(
    pt: NavPoint, file: str, out: list[str],
) -> None:
    """Append ``pt`` and its descendants' anchors when they are in ``file``."""
    if pt.anchor and pt.file == file:
        out.append(pt.anchor)
    for child in pt.children:
        _collect_same_file_anchors(child, file, out)


def _find_path(
    target: NavPoint, roots: list[NavPoint],
) -> list[NavPoint] | None:
    """Ancestor chain ending at target (inclusive), or None."""
    for root in roots:
        if root is target:
            return [root]
        found = _find_path(target, root.children)
        if found is not None:
            return [root, *found]
    return None


def _flatten_navpoints(points: list[NavPoint]) -> list[NavPoint]:
    """Flatten nested NavPoint tree into a flat list."""
    result: list[NavPoint] = []
    for pt in points:
        result.append(pt)
        result.extend(_flatten_navpoints(pt.children))
    return result


def _group_under_parts(points: list[NavPoint]) -> list[NavPoint]:
    """Group chapters under their preceding part (flat NCX only)."""
    # Skip if parts already have children (nested pattern)
    if any(p.nav_type == "part" and p.children for p in points):
        return points

    result: list[NavPoint] = []
    current_part: NavPoint | None = None

    for pt in points:
        if pt.nav_type == "part":
            current_part = pt
            result.append(pt)
        elif pt.nav_type == "chapter" and current_part is not None:
            current_part.children.append(pt)
        else:
            if pt.nav_type == "back_matter":
                current_part = None
            result.append(pt)

    return result


@app.command()
def search(
    ctx: typer.Context,
    path: Path | None = typer.Argument(None, help="Path to EPUB file."),
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
) -> None:
    """Full-text BM25 search across an EPUB's sections."""
    epub_path = _require_path(ctx, path)
    if query is None:
        console.print("[red]Error:[/red] Missing required argument: QUERY\n")
        console.print(ctx.get_help())
        raise typer.Exit(1)
    if group not in ("section", "chapter", "flat"):
        console.print("[red]Error:[/red] --group must be section, chapter, or flat\n")
        raise typer.Exit(1)
    if fmt is not None and not show_content:
        console.print(
            "[red]Error:[/red] --format requires --show-content\n"
        )
        raise typer.Exit(1)
    if fmt is not None and fmt not in ("html", "plaintext", "markdown"):
        console.print(
            "[red]Error:[/red] --format must be html, plaintext, or markdown\n"
        )
        raise typer.Exit(1)
    content_format = fmt or "html"

    try:
        hits = run_search(
            str(epub_path), query, group=group, limit=limit, output_dir=output_dir,
            with_content=show_content, content_format=content_format,
        )
    except InvalidEpubError as e:
        console.print(f"[red]Error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}\n")
        console.print(ctx.get_help())
        raise typer.Exit(1) from None

    if not hits:
        console.print(f"[yellow]No matches for[/yellow] {query!r}")
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


def cli_entry() -> None:
    """Entry point for pyproject.toml."""
    app()
