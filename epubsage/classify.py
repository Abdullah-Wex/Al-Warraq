"""NavPoint classification — chapter, part, front/back matter detection."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from .ncx import NavPoint

_XHTML_NS = "http://www.w3.org/1999/xhtml"
_EPUB_NS = "http://www.idpf.org/2007/ops"

# Signal 1: Semantic ID prefixes (O'Reilly, etc.)
_ID_PREFIXES: dict[str, str] = {
    "chapter-": "chapter",
    "preface-": "front_matter",
    "part-": "part",
    "appendix-": "back_matter",
    "bibliography-": "back_matter",
    "index-": "back_matter",
    "colophon-": "back_matter",
    "afterword-": "back_matter",
}
_GENERIC_ID_RE = re.compile(r"^(navPoint|navpoint|d\d+e|np|i\d+$|uuid|toc\d|sep_)", re.I)

# Signal 2: Label patterns
_CHAPTER_NUM_RE = re.compile(r"^\d+[\.\s:]")
_CHAPTER_WORD_RE = re.compile(r"^Chapter\s+\d+", re.I)
_PART_ROMAN_RE = re.compile(r"^[IVXLC]+[\.\s:]")
_PART_WORD_RE = re.compile(r"^(Part|Section)\s+(\d+|[IVXLC]+)", re.I)
_APPENDIX_LETTER_RE = re.compile(r"^[A-F][\.\s:]")

_FRONT_MATTER_LABELS: frozenset[str] = frozenset({
    "cover", "cover page", "half title", "halftitle page",
    "title", "title page", "copyright", "copyright page",
    "dedication", "dedication page",
    "contents", "table of contents", "brief table of contents",
    "brief contents", "contents at a glance", "contents in detail",
    "front matter", "foreword", "preface", "introduction",
    "acknowledgments", "acknowledgements",
    "about this book", "about this ebook",
    "about the author", "about the authors",
    "about the technical reviewer",
    "dear reader", "notes on usage", "contributors", "about packt",
    "half title page", "series", "series page", "editors",
    "abstract", "author's note", "author’s note",  # noqa: RUF001
    "about the book", "book changelog", "changelog",
    "about the cover illustration",
    "inside front cover",
    "praise for the first edition", "praise for this book",
})

_BACK_MATTER_LABELS: frozenset[str] = frozenset({
    "back matter", "index", "bibliography", "glossary", "colophon",
    "afterword", "references", "other books you may enjoy", "back cover",
    "inside back cover",
})

# Signal 3: Filename patterns
_FILE_CHAPTER_RE = re.compile(
    r"(^ch\d|^\d+[\._\-]|chapter[_\-]|_Chapter\.)", re.I,
)
_FILE_PART_RE = re.compile(
    r"(^part\d|part[_\-]|Part_\d|^p\d+\.)", re.I,
)
_FILE_FRONT_RE = re.compile(
    r"(^preface|^pref0|^fm\.|^title[_.]|^copyright[_.]|^dedication[_.]"
    r"|^toc\.|^cover[_.]|^btoc\.|^halftitle|^dedi\."
    r"|Frontmatter|BookFrontmatter"
    r"|^foreword|^acknowledgment|about-this-book|about-the-author"
    r"|^ch00_fm)",
    re.I,
)
_FILE_BACK_RE = re.compile(
    r"(^ix\d|^index[_.]|Index\.|^app\d|^appendix|appendix[_\-]"
    r"|^bibliography|^glossary|^afterword"
    r"|Backmatter|BookBackmatter|_Index\.|_BM\.)",
    re.I,
)


_BARE_DIGIT_RE = re.compile(r"^\d+$")
_OPAQUE_FN_RE = re.compile(
    r"^([0-9a-f]{8}-|uuid-|Section\d|B\d+_\d|[0-9a-f]{16})", re.I,
)
_CHAP_H1_RE = re.compile(r"^(chapter|appendix|part)\s*\d+\b|^\d+[\.\s:]", re.I)
_FM_H1_WORDS = frozenset({
    "preface", "introduction", "foreword", "acknowledgments",
    "acknowledgements", "dedication", "about the author", "contributors",
    "copyright", "cover",
})
_BM_H1_WORDS = frozenset({
    "index", "bibliography", "glossary", "appendix", "afterword", "references",
})

_SIG_CACHE: dict[str, dict[str, str | None]] = {}


def _read_file_signals(abs_path: str) -> dict[str, str | None]:
    """Open an XHTML chapter file and extract classification signals.

    Returns ``{"epub_type": ..., "h1": ...}``. Cached per absolute path so
    repeated lookups during a single TOC walk are free.
    """
    if abs_path in _SIG_CACHE:
        return _SIG_CACHE[abs_path]
    sig: dict[str, str | None] = {"epub_type": None, "h1": None}
    try:
        tree = ET.parse(abs_path)  # noqa: S314
        root = tree.getroot()
        body = root.find(f".//{{{_XHTML_NS}}}body") or root.find(".//body")
        if body is not None:
            sig["epub_type"] = (
                body.get(f"{{{_EPUB_NS}}}type") or body.get("epub:type")
            )
        if not sig["epub_type"]:
            for el in root.iter():
                et = el.get(f"{{{_EPUB_NS}}}type") or el.get("epub:type")
                if et:
                    sig["epub_type"] = et
                    break
        for tag in (f"{{{_XHTML_NS}}}h1", "h1", f"{{{_XHTML_NS}}}h2", "h2"):
            h = root.find(f".//{tag}")
            if h is not None:
                sig["h1"] = "".join(h.itertext()).strip()[:80]
                break
    except (ET.ParseError, OSError):
        pass
    _SIG_CACHE[abs_path] = sig
    return sig


def classify_navpoint(nav_point: NavPoint) -> str:
    """Classify a NavPoint as chapter, part, front_matter, back_matter, or section.

    Tries (in order): semantic ID prefix, label text patterns, filename
    patterns, bare-digit labels, and finally — for opaque filenames
    (UUIDs, hash-prefixed) — reads the chapter file for ``epub:type``
    and ``<h1>`` signals.
    """
    np_id = nav_point.id
    label = nav_point.label.strip()
    label_lower = label.lower()
    filename = nav_point.file.rsplit("/", 1)[-1] if nav_point.file else ""

    # Signal 1: semantic ID prefix
    if not _GENERIC_ID_RE.match(np_id):
        for prefix, nav_type in _ID_PREFIXES.items():
            if np_id.startswith(prefix):
                return nav_type

    # Signal 2: label text
    if label_lower in _FRONT_MATTER_LABELS:
        return "front_matter"
    if label_lower in _BACK_MATTER_LABELS:
        return "back_matter"
    if label_lower.startswith("appendix"):
        return "back_matter"
    if _CHAPTER_NUM_RE.match(label) or _CHAPTER_WORD_RE.match(label):
        return "chapter"
    if _PART_ROMAN_RE.match(label) or _PART_WORD_RE.match(label):
        return "part"
    if _APPENDIX_LETTER_RE.match(label):
        return "back_matter"

    # Signal 3: filename (specific patterns before broad ones)
    if _FILE_FRONT_RE.search(filename):
        return "front_matter"
    if _FILE_BACK_RE.search(filename):
        return "back_matter"
    if _FILE_CHAPTER_RE.search(filename):
        return "chapter"
    if _FILE_PART_RE.search(filename):
        return "part"

    # Signal 4: bare digit labels (Packt Pvt Ltd-style split chapter NCX)
    if _BARE_DIGIT_RE.match(label):
        return "chapter"

    # Signal 5: opaque filename → consult the chapter file's epub:type / <h1>
    if filename and _OPAQUE_FN_RE.match(filename) and nav_point.abs_file:
        sig = _read_file_signals(nav_point.abs_file)
        et = (sig.get("epub_type") or "").lower()
        if "frontmatter" in et or "preface" in et or "titlepage" in et:
            return "front_matter"
        if "backmatter" in et or "appendix" in et or "index" in et:
            return "back_matter"
        if "chapter" in et:
            return "chapter"
        if "part" in et:
            return "part"
        h = (sig.get("h1") or "").strip()
        if h:
            if _CHAP_H1_RE.match(h):
                return "chapter"
            hl = h.lower()
            if hl in _FM_H1_WORDS:
                return "front_matter"
            if hl in _BM_H1_WORDS:
                return "back_matter"

    return "section"


def merge_same_file_runs(points: list[NavPoint]) -> list[NavPoint]:
    """Collapse Packt-style split chapter pairs.

    Some publishers (notably Packt's "Pvt Ltd" imprint) emit two
    consecutive top-level navPoints per chapter — one with a bare-digit
    label (``"1"``) and one with the chapter title — both pointing to the
    same file. This merges each such run into a single
    ``"1. <title>"``-style chapter, attaching the run's other entries as
    children.
    """
    if not points:
        return points
    out: list[NavPoint] = []
    i = 0
    while i < len(points):
        run = [points[i]]
        j = i + 1
        while (
            j < len(points)
            and points[j].file
            and points[j].file == points[i].file
        ):
            run.append(points[j])
            j += 1
        if len(run) >= 2:
            num = next(
                (p.label for p in run if _BARE_DIGIT_RE.match(p.label.strip())),
                None,
            )
            descr = next(
                (p for p in run
                 if not _BARE_DIGIT_RE.match(p.label.strip())
                 and len(p.label.strip()) > 3),
                None,
            )
            if num and descr:
                inner = [
                    p for p in run
                    if p is not descr
                    and not _BARE_DIGIT_RE.match(p.label.strip())
                ]
                merged = NavPoint(
                    id=descr.id,
                    label=f"{num}. {descr.label}",
                    src=descr.src,
                    file=descr.file,
                    anchor=descr.anchor,
                    children=inner + descr.children,
                    play_order=descr.play_order,
                    class_name=descr.class_name,
                    abs_file=descr.abs_file,
                )
                out.append(merged)
            else:
                out.extend(run)
        else:
            out.append(run[0])
        i = j
    return out


def _is_numeric_chapter_label(label: str) -> bool:
    """Label starts with a chapter number ("1.", "Chapter 1", "1 …")."""
    label = label.strip()
    return bool(
        _CHAPTER_NUM_RE.match(label) or _CHAPTER_WORD_RE.match(label),
    )


def refine_positional(points: list[NavPoint]) -> None:
    """Promote stray ``section`` entries flanking numeric chapters to FM/BM.

    Manning and similar publishers ship unusual front/back-matter labels
    ("inside front cover", "Praise for the First Edition", "about the
    cover illustration") that lack standard keywords and fall to
    ``section``. Anything still ``section`` before the first numeric
    chapter is front-matter; anything after the last numeric chapter is
    back-matter.
    """
    chap_idx = [
        i for i, pt in enumerate(points)
        if pt.nav_type == "chapter" and _is_numeric_chapter_label(pt.label)
    ]
    if not chap_idx:
        return
    first, last = chap_idx[0], chap_idx[-1]
    for i, pt in enumerate(points):
        if pt.nav_type != "section":
            continue
        if i < first:
            pt.nav_type = "front_matter"
        elif i > last:
            pt.nav_type = "back_matter"


def refine_structural(points: list[NavPoint]) -> None:
    """Promote top-level ``section`` entries bracketed by parts to ``chapter``.

    For Pattern-B books (one file per section, opaque filenames) the
    chapter labels are bare topical phrases — no number, no chapter
    keyword. Position is the only signal. If a top-level section sits
    between two ``part`` entries (or between a ``part`` and a later
    ``part``/``back_matter``), it is a chapter.
    """
    # Index of every part marker.
    part_positions = [i for i, p in enumerate(points) if p.nav_type == "part"]
    if not part_positions:
        return
    # A section is "between parts" if at least one part precedes it.
    first_part = part_positions[0]
    for i, pt in enumerate(points):
        if pt.nav_type != "section":
            continue
        if i <= first_part:
            continue
        pt.nav_type = "chapter"


def classify_children(points: list[NavPoint]) -> None:
    """Classify children of already-classified nav_points by nesting depth."""
    for pt in points:
        if pt.nav_type in ("chapter", "part", "front_matter", "back_matter"):
            _assign_child_types(
                pt.children, depth=1,
                parent_type=pt.nav_type, parent_file=pt.file,
            )
        elif pt.children:
            classify_children(pt.children)


def _depth_label(depth: int) -> str:
    if depth == 1:
        return "section"
    if depth == 2:
        return "subsection"
    return "minor"


def _assign_child_types(
    children: list[NavPoint],
    depth: int,
    parent_type: str | None = None,
    parent_file: str | None = None,
) -> None:
    """Classify children using ``classify_navpoint`` first, then depth labels.

    When a child shares its parent's file it is a sub-section within that
    document and gets a depth-based label (``section``/``subsection``/
    ``minor``). When the child has its own file we try ``classify_navpoint``
    so nested chapters under parts (Pearson, Addison-Wesley) and the like
    are promoted correctly. Front/back-matter promotion under a chapter is
    suppressed — a label like "Introduction" sitting inside a chapter is a
    section, not front matter.
    """
    for child in children:
        if child.nav_type is None:
            if child.file and child.file == parent_file:
                child.nav_type = _depth_label(depth)
            else:
                attempt = classify_navpoint(child)
                if (attempt in ("front_matter", "back_matter")
                        and parent_type == "chapter"):
                    attempt = "section"
                child.nav_type = (
                    attempt if attempt != "section" else _depth_label(depth)
                )
        next_depth: int
        next_parent: str | None
        next_file: str | None
        if child.nav_type in (
            "chapter", "part", "front_matter", "back_matter",
        ):
            next_depth = 1
            next_parent = child.nav_type
            next_file = child.file
        else:
            next_depth = depth + 1
            next_parent = parent_type
            next_file = parent_file
        _assign_child_types(
            child.children, next_depth, next_parent, next_file,
        )
