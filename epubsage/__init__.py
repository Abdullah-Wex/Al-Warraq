"""epubsage — lightweight EPUB inspection library.

Deprecated: renamed to al-warraq (``pip install al-warraq``, ``import al_warraq``).
"""

from .classify import (
    classify_children,
    classify_navpoint,
    merge_same_file_runs,
    refine_positional,
    refine_structural,
)
from .content import Section, extract_all_sections, extract_content
from .epub import extract_epub, find_opf, hash_epub
from .exceptions import EpubSageError, InvalidEpubError
from .nav import parse_nav
from .ncx import NavPoint, NcxData, parse_ncx
from .opf import EpubInfo, TocInfo, parse_opf
from .search import SearchHit, build_search_index, search, tokenize
from .storage import resolve_output_dir

__version__ = "0.7.1"

import warnings as _warnings

_warnings.warn(
    "epubsage has been renamed: pip install al-warraq, import al_warraq. "
    "The epubsage package will receive no further updates.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "EpubInfo",
    "EpubSageError",
    "InvalidEpubError",
    "NavPoint",
    "NcxData",
    "SearchHit",
    "Section",
    "TocInfo",
    "build_search_index",
    "classify_children",
    "classify_navpoint",
    "extract_all_sections",
    "extract_content",
    "extract_epub",
    "find_opf",
    "hash_epub",
    "inspect_epub",
    "merge_same_file_runs",
    "parse_nav",
    "parse_ncx",
    "parse_opf",
    "refine_positional",
    "refine_structural",
    "search",
    "tokenize",
]


def inspect_epub(epub_path: str, output_dir: str | None = None) -> EpubInfo:
    """Hash, extract, parse OPF, detect TOC type."""
    extract_dir = extract_epub(epub_path, output_dir or resolve_output_dir())
    opf_path = find_opf(str(extract_dir))
    return parse_opf(str(opf_path), str(extract_dir))
