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
from .content_store import (
    ContentStore,
    LocalContentStore,
    MinioContentStore,
    get_minio_content_store,
    sha256_hex,
)
from .epub import extract_epub, find_opf, hash_epub
from .exceptions import (
    AlWarraqError,
    BlobNotFoundError,
    InvalidEpubError,
    SectionNotFoundError,
    TocNotFoundError,
)
from .hooks import Embedder, PassageSplitter, StructuralSplitter
from .nav import parse_nav
from .ncx import NavPoint, NcxData, parse_ncx
from .opf import EpubInfo, TocInfo, parse_opf
from .processing import (
    SCHEMA_VERSION,
    BookMetadata,
    Passage,
    ProcessedBook,
    ProcessedChapter,
    process_epub,
)
from .search import SearchHit, build_search_index, search, tokenize
from .storage import resolve_output_dir

__version__ = "1.0.0"

__all__ = [
    "SCHEMA_VERSION",
    "AlWarraqError",
    "BlobNotFoundError",
    "Book",
    "BookMetadata",
    "ContentStore",
    "Embedder",
    "EpubInfo",
    "InvalidEpubError",
    "LocalContentStore",
    "MinioContentStore",
    "NavPoint",
    "NcxData",
    "Passage",
    "PassageSplitter",
    "ProcessedBook",
    "ProcessedChapter",
    "SearchHit",
    "Section",
    "SectionContent",
    "SectionNotFoundError",
    "StructuralSplitter",
    "TocInfo",
    "TocNotFoundError",
    "build_search_index",
    "classify_children",
    "classify_navpoint",
    "extract_all_sections",
    "extract_content",
    "extract_epub",
    "find_opf",
    "get_minio_content_store",
    "hash_epub",
    "inspect_epub",
    "merge_same_file_runs",
    "parse_nav",
    "parse_ncx",
    "parse_opf",
    "process_epub",
    "refine_positional",
    "refine_structural",
    "resolve_output_dir",
    "search",
    "sha256_hex",
    "tokenize",
]
