"""Al-Warraq (الورّاق) — lightweight EPUB inspection library.

Install: ``pip install al-warraq`` · Import: ``import al_warraq``
"""

from .book import Book, SectionContent, inspect_epub
from .classify import (
    classify_children,
    classify_navpoint,
    merge_same_file_runs,
    refine_positional,
    refine_structural,
)
from .content import Section, extract_all_sections, extract_content
from .epub import extract_epub, find_opf, hash_epub
from .exceptions import (
    AlWarraqError,
    InvalidEpubError,
    SectionNotFoundError,
    TocNotFoundError,
)
from .nav import parse_nav
from .ncx import NavPoint, NcxData, parse_ncx
from .opf import EpubInfo, TocInfo, parse_opf
from .search import SearchHit, build_search_index, search, tokenize
from .storage import resolve_output_dir

__version__ = "1.0.0"

__all__ = [
    "AlWarraqError",
    "Book",
    "EpubInfo",
    "InvalidEpubError",
    "NavPoint",
    "NcxData",
    "SearchHit",
    "Section",
    "SectionContent",
    "SectionNotFoundError",
    "TocInfo",
    "TocNotFoundError",
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
    "resolve_output_dir",
    "search",
    "tokenize",
]
