"""Shared TOC helpers: parse + classify a book's table of contents.

Functional core used by both search indexing and the processing pipeline —
pure transforms over an already-extracted EPUB directory.
"""

from __future__ import annotations

from pathlib import Path

from .classify import (
    classify_children,
    classify_navpoint,
    merge_same_file_runs,
    refine_positional,
    refine_structural,
)
from .epub import find_opf
from .nav import parse_nav
from .ncx import NavPoint, parse_ncx
from .opf import parse_opf


def classified_roots(extract_dir: Path) -> tuple[list[NavPoint], str, Path]:
    """Parse, classify and merge the TOC; return (roots, book_title, opf_dir).

    ``opf_dir`` is the base directory for resolving NavPoint ``file`` paths
    (they are relative to the OPF, not the zip root). A book without a TOC
    yields no roots — a valid state, not an error.
    """
    opf_path = find_opf(str(extract_dir))
    info = parse_opf(str(opf_path), str(extract_dir))
    opf_dir = Path(opf_path).parent

    if info.toc.ncx_path:
        ncx = parse_ncx(str(info.toc.ncx_path))
        roots = ncx.nav_points
        title = ncx.doc_title or info.title or "(untitled)"
    elif info.toc.toc_path:
        roots = parse_nav(str(info.toc.toc_path))
        title = info.title or "(untitled)"
    else:
        return [], info.title or "(untitled)", opf_dir

    roots = merge_same_file_runs(roots)
    for pt in roots:
        pt.nav_type = classify_navpoint(pt)
    refine_structural(roots)
    refine_positional(roots)
    classify_children(roots)
    return roots, title, opf_dir


def anchors_by_file(roots: list[NavPoint]) -> dict[str, list[str]]:
    """All TOC anchors grouped by their file (for boundary detection)."""
    out: dict[str, list[str]] = {}

    def walk(points: list[NavPoint]) -> None:
        for pt in points:
            if pt.file and pt.anchor:
                out.setdefault(pt.file, []).append(pt.anchor)
            walk(pt.children)

    walk(roots)
    return out


def descendant_anchors(points: list[NavPoint]) -> list[str]:
    """Anchors of every descendant (used as non-boundary child anchors)."""
    out: list[str] = []
    for pt in points:
        if pt.anchor:
            out.append(pt.anchor)
        out.extend(descendant_anchors(pt.children))
    return out
