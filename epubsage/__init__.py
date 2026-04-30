"""epubsage — lightweight EPUB inspection library."""

from .classify import classify_children, classify_navpoint
from .content import Section, extract_all_sections, extract_content
from .epub import extract_epub, find_opf, hash_epub
from .exceptions import EpubSageError, InvalidEpubError
from .nav import parse_nav
from .ncx import NavPoint, NcxData, parse_ncx
from .opf import EpubInfo, TocInfo, parse_opf
from .storage import resolve_output_dir

__version__ = "0.5.0"

__all__ = [
    "EpubInfo",
    "EpubSageError",
    "InvalidEpubError",
    "NavPoint",
    "NcxData",
    "Section",
    "TocInfo",
    "classify_children",
    "classify_navpoint",
    "extract_all_sections",
    "extract_content",
    "extract_epub",
    "find_opf",
    "hash_epub",
    "inspect_epub",
    "parse_nav",
    "parse_ncx",
    "parse_opf",
]


def inspect_epub(epub_path: str, output_dir: str | None = None) -> EpubInfo:
    """Hash, extract, parse OPF, detect TOC type."""
    extract_dir = extract_epub(epub_path, output_dir or resolve_output_dir())
    opf_path = find_opf(str(extract_dir))
    return parse_opf(str(opf_path), str(extract_dir))
