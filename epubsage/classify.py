"""NavPoint classification — chapter, part, front/back matter detection."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ncx import NavPoint

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
    "brief contents", "contents at a glance",
    "front matter", "foreword", "preface", "introduction",
    "acknowledgments", "acknowledgements",
    "about this book", "about this ebook",
    "about the author", "about the authors",
    "about the technical reviewer",
    "dear reader", "notes on usage", "contributors", "about packt",
    "half title page", "series", "series page", "editors",
})

_BACK_MATTER_LABELS: frozenset[str] = frozenset({
    "back matter", "index", "bibliography", "glossary", "colophon",
    "afterword", "references", "other books you may enjoy", "back cover",
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


def classify_navpoint(nav_point: NavPoint) -> str:
    """Classify a NavPoint as chapter, part, front_matter, back_matter, or section."""
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

    return "section"


def classify_children(points: list[NavPoint]) -> None:
    """Classify children of already-classified nav_points by nesting depth."""
    for pt in points:
        if pt.nav_type in ("chapter", "part", "front_matter", "back_matter"):
            _assign_child_types(pt.children, depth=1)
        elif pt.children:
            classify_children(pt.children)


def _assign_child_types(children: list[NavPoint], depth: int) -> None:
    """Assign section/subsection/minor based on depth under parent."""
    for child in children:
        if child.nav_type is None:
            if depth == 1:
                child.nav_type = "section"
            elif depth == 2:
                child.nav_type = "subsection"
            else:
                child.nav_type = "minor"
        _assign_child_types(child.children, depth + 1)
