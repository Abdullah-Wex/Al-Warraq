"""Book — the high-level way to work with an EPUB.

Open a book once, then ask it questions:

    from al_warraq import Book

    book = Book.open("book.epub")
    book.title                                   # "Quick Start Guide to ..."
    book.toc()                                   # classified chapter tree
    book.search("transformers")                  # ranked BM25 hits
    book.section(anchor="ch01lev1sec1",
                 output_format="markdown")       # one SectionContent

Book is the facade over the lower-level modules (opf, ncx, nav, content,
search). Everything that answers "how do I find and bound a section?" lives
here, so every frontend — CLI, TUI, or another application — shares one
implementation instead of re-deriving it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .classify import (
    classify_children,
    classify_navpoint,
    merge_same_file_runs,
    refine_positional,
    refine_structural,
)
from .content import extract_content
from .epub import extract_epub, find_opf, hash_epub
from .exceptions import SectionNotFoundError, TocNotFoundError
from .nav import parse_nav
from .ncx import NavPoint, parse_ncx
from .opf import EpubInfo, parse_opf
from .search import SearchHit
from .search import search as search_epub
from .storage import resolve_output_dir


def inspect_epub(epub_path: str, output_dir: str | None = None) -> EpubInfo:
    """Hash, extract, parse OPF, detect TOC type."""
    extract_dir = extract_epub(epub_path, output_dir or resolve_output_dir())
    opf_path = find_opf(str(extract_dir))
    return parse_opf(str(opf_path), str(extract_dir))


@dataclass
class SectionContent:
    """One section's extracted content, with where it came from."""

    file: str
    anchor: str | None
    output_format: str
    text: str


class Book:
    """An opened EPUB: inspected once, queried many times."""

    def __init__(self, path: str, info: EpubInfo, output_dir: str) -> None:
        self.path = path
        self.info = info
        self.output_dir = output_dir
        self._toc: list[NavPoint] | None = None
        self._doc_title: str | None = None
        self._hash: str | None = None

    @classmethod
    def open(cls, path: str | Path, output_dir: str | None = None) -> Book:
        """Extract and inspect an EPUB, returning a queryable Book."""
        out = output_dir or resolve_output_dir()
        info = inspect_epub(str(path), out)
        return cls(str(path), info, out)

    # ---------------------------------------------------------------- basics

    @property
    def title(self) -> str | None:
        return self.info.title

    @property
    def version(self) -> str:
        return self.info.version

    @property
    def toc_type(self) -> str:
        return self.info.toc.toc_type

    @property
    def hash(self) -> str:
        """Content hash of the EPUB file (stable id for caching/dedup)."""
        if self._hash is None:
            self._hash = hash_epub(self.path)
        return self._hash

    @property
    def doc_title(self) -> str:
        """Best available display title: TOC title, then metadata, then a stub."""
        self.toc()  # fills _doc_title as a side effect of parsing
        return self._doc_title or self.title or "(untitled)"

    # ------------------------------------------------------------------- toc

    def toc(self) -> list[NavPoint]:
        """The table of contents as a classified tree.

        Entries are classified (chapter / part / front matter / section ...)
        and flat chapter lists are grouped under their parts. The result is
        parsed once and cached.
        """
        if self._toc is not None:
            return self._toc

        raw = self._parse_toc()
        raw = merge_same_file_runs(raw)
        for point in raw:
            point.nav_type = classify_navpoint(point)
        refine_structural(raw)
        refine_positional(raw)
        classify_children(raw)
        self._toc = _group_chapters_under_parts(raw)
        return self._toc

    def flat_toc(self) -> list[NavPoint]:
        """Every TOC entry (all nesting levels) as one flat list."""
        return _flatten(self.toc())

    def _parse_toc(self) -> list[NavPoint]:
        """Read nav points from NCX or NAV, remembering the document title."""
        toc = self.info.toc
        if toc.ncx_path:
            ncx = parse_ncx(str(toc.ncx_path))
            self._doc_title = ncx.doc_title
            return ncx.nav_points
        if toc.toc_path:
            return parse_nav(str(toc.toc_path))
        raise TocNotFoundError("No table of contents found.")

    # ---------------------------------------------------------------- search

    def search(
        self,
        query: str,
        *,
        group: str = "section",
        limit: int = 10,
        with_content: bool = False,
        content_format: str = "html",
    ) -> list[SearchHit]:
        """Ranked BM25 search across the book's sections."""
        return search_epub(
            self.path, query, group=group, limit=limit,
            output_dir=self.output_dir,
            with_content=with_content, content_format=content_format,
        )

    # --------------------------------------------------------------- section

    def section(
        self,
        anchor: str | None = None,
        file: str | None = None,
        *,
        output_format: str | None = None,
        exclude: list[str] | None = None,
    ) -> SectionContent:
        """Extract one TOC section's content by anchor and/or file.

        The section's boundaries come from the TOC tree: content stops at the
        next sibling section, child sections are kept, and anchors from other
        chapters never truncate it.
        """
        if anchor is None and file is None:
            raise ValueError("Provide an anchor or a file.")

        target = self._find_target(anchor, file)
        html_path = self._resolve_html_path(target)

        all_points = self.flat_toc()
        same_file_anchors = [
            pt.anchor for pt in all_points
            if pt.file == target.file and pt.anchor is not None
        ]
        child_anchors = _descendant_anchors(target)
        stop_anchors = _following_sibling_anchors(target, self.toc())

        text = extract_content(
            str(html_path), target.anchor, same_file_anchors,
            child_anchors, exclude, output_format=output_format,
            stop_anchors=stop_anchors,
        )
        return SectionContent(
            file=target.file,
            anchor=target.anchor,
            output_format=output_format or "html",
            text=text,
        )

    def _find_target(self, anchor: str | None, file: str | None) -> NavPoint:
        """Find the TOC entry the caller is asking for."""
        all_points = self.flat_toc()

        if file is not None:
            toc_file = _match_toc_file(file, all_points)
            if toc_file is None:
                raise SectionNotFoundError(f"File '{file}' not found in TOC")
            target = next(
                (pt for pt in all_points
                 if pt.file == toc_file and pt.anchor == anchor),
                None,
            )
            if target is None:
                # The file exists in the TOC but has no entry for this exact
                # anchor — extract the whole file from its first entry.
                target = next(pt for pt in all_points if pt.file == toc_file)
                target = NavPoint(
                    id=target.id, label=target.label, src=target.src,
                    file=toc_file, anchor=anchor, abs_file=target.abs_file,
                )
            return target

        target = next((pt for pt in all_points if pt.anchor == anchor), None)
        if target is None:
            raise SectionNotFoundError(f"Anchor '{anchor}' not found in TOC")
        return target

    def _resolve_html_path(self, target: NavPoint) -> Path:
        """Absolute path of the chapter file behind a TOC entry."""
        if target.abs_file:
            html_path = Path(target.abs_file)
        else:
            html_path = (self.info.opf_path.parent / target.file).resolve()
        if not html_path.exists():
            raise SectionNotFoundError(f"File not found: {html_path}")
        return html_path


# ------------------------------------------------------- tree walking helpers


def _flatten(points: list[NavPoint]) -> list[NavPoint]:
    """Nested NavPoint tree -> flat list, depth-first."""
    result: list[NavPoint] = []
    for pt in points:
        result.append(pt)
        result.extend(_flatten(pt.children))
    return result


def _match_toc_file(file_input: str, all_points: list[NavPoint]) -> str | None:
    """Match user input to a TOC file: exact path first, then by filename."""
    for pt in all_points:
        if pt.file == file_input:
            return pt.file
    input_name = file_input.rsplit("/", 1)[-1]
    for pt in all_points:
        if pt.file.rsplit("/", 1)[-1] == input_name:
            return pt.file
    return None


def _descendant_anchors(pt: NavPoint) -> list[str]:
    """Anchor ids of every descendant of a TOC entry."""
    anchors: list[str] = []
    for child in pt.children:
        if child.anchor:
            anchors.append(child.anchor)
        anchors.extend(_descendant_anchors(child))
    return anchors


def _following_sibling_anchors(
    target: NavPoint, roots: list[NavPoint],
) -> list[str] | None:
    """Boundary anchors for ``target``: where its section must stop.

    Collects the anchors of every TOC sibling that follows ``target`` (and
    their descendants) at each level of the ancestry chain, filtered to
    ``target.file``. Filtering by file matters because some publishers
    (e.g. Manning) restart anchor numbering per chapter, so an id from a
    later chapter can collide with one inside the current chapter and
    truncate it.
    """
    path = _path_to(target, roots)
    if path is None:
        return None
    stops: list[str] = []
    for depth, node in enumerate(path):
        siblings = roots if depth == 0 else path[depth - 1].children
        for sibling in siblings[siblings.index(node) + 1:]:
            _collect_anchors_in_file(sibling, target.file, stops)
    return stops


def _collect_anchors_in_file(pt: NavPoint, file: str, out: list[str]) -> None:
    """Append the anchors of ``pt`` and its descendants that live in ``file``."""
    if pt.anchor and pt.file == file:
        out.append(pt.anchor)
    for child in pt.children:
        _collect_anchors_in_file(child, file, out)


def _path_to(
    target: NavPoint, roots: list[NavPoint],
) -> list[NavPoint] | None:
    """Ancestor chain from a root down to ``target`` (inclusive), or None."""
    for root in roots:
        if root is target:
            return [root]
        found = _path_to(target, root.children)
        if found is not None:
            return [root, *found]
    return None


def _group_chapters_under_parts(points: list[NavPoint]) -> list[NavPoint]:
    """Move chapters under their preceding part (flat NCX pattern only)."""
    already_nested = any(p.nav_type == "part" and p.children for p in points)
    if already_nested:
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
