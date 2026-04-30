"""OPF parsing — version detection and TOC type discovery."""

import html
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from .exceptions import InvalidEpubError

OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"


@dataclass
class TocInfo:
    """TOC detection result."""

    toc_type: str  # "nav", "ncx", or "unknown"
    toc_href: str | None = None  # relative path from OPF dir
    toc_path: Path | None = None  # absolute resolved path
    ncx_href: str | None = None  # NCX href (always populated if NCX exists)
    ncx_path: Path | None = None  # NCX resolved path


@dataclass
class EpubInfo:
    """EPUB inspection result."""

    version: str  # "2.0", "3.0", etc.
    toc: TocInfo
    opf_path: Path
    title: str | None = None
    publisher: str | None = None
    creator: str | None = None


def parse_opf(opf_path: str, epub_dir: str | None = None) -> EpubInfo:
    """Parse OPF file for version and TOC type."""
    path = Path(opf_path)

    try:
        tree = ET.parse(opf_path)  # noqa: S314
    except ET.ParseError as e:
        raise InvalidEpubError(f"Failed to parse OPF as XML: {e}") from e

    root = tree.getroot()

    # Version detection
    version = root.get("version")
    if not version:
        raise InvalidEpubError(
            "OPF root element missing 'version' attribute — cannot determine EPUB version"
        )

    # Dublin Core fields — HTML-unescape so numeric entities decode
    # (e.g. ``O&#8217;Reilly`` → ``O'Reilly``).
    title = _dc_text(root, "title")
    publisher = _dc_text(root, "publisher")
    creator = _dc_text(root, "creator")

    # TOC detection from manifest
    toc = _detect_toc(root, path.parent, epub_dir)

    return EpubInfo(
        version=version,
        toc=toc,
        opf_path=path,
        title=title,
        publisher=publisher,
        creator=creator,
    )


def _dc_text(root: ET.Element, tag: str) -> str | None:
    """Return a Dublin Core element's text, HTML-unescaped, or None."""
    el = root.find(f".//{{{DC_NS}}}{tag}")
    if el is not None and el.text:
        return html.unescape(el.text.strip())
    return None


def _detect_toc(root: ET.Element, opf_dir: Path, epub_dir: str | None) -> TocInfo:
    """Detect TOC type and location from manifest items."""
    manifest = root.find(f"{{{OPF_NS}}}manifest")
    if manifest is None:
        manifest = root.find("manifest")
    if manifest is None:
        return TocInfo(toc_type="unknown")

    items = manifest.findall(f"{{{OPF_NS}}}item")
    if not items:
        items = manifest.findall("item")

    # Always find NCX from manifest
    ncx_href: str | None = None
    ncx_path: Path | None = None
    for item in items:
        if item.get("media-type") == "application/x-dtbncx+xml":
            href = item.get("href", "")
            if href:
                ncx_href = href
                if epub_dir:
                    resolved = (opf_dir / href).resolve()
                    if resolved.exists():
                        ncx_path = resolved
            break

    # Fallback: check common NCX paths if not in manifest
    if ncx_path is None and epub_dir:
        epub_base = Path(epub_dir)
        for name in ["toc.ncx", "OEBPS/toc.ncx", "OPS/toc.ncx"]:
            candidate = epub_base / name
            if candidate.exists():
                ncx_href = name
                ncx_path = candidate
                break

    # Detect primary TOC type
    # EPUB 3: look for nav property
    for item in items:
        props = item.get("properties", "")
        if "nav" in props:
            href = item.get("href", "")
            if href:
                info = _build_toc_info("nav", href, opf_dir, epub_dir)
                info.ncx_href = ncx_href
                info.ncx_path = ncx_path
                return info

    # EPUB 2: NCX is primary
    if ncx_href:
        return TocInfo(
            toc_type="ncx", toc_href=ncx_href, toc_path=ncx_path,
            ncx_href=ncx_href, ncx_path=ncx_path,
        )

    # Fallback: check common NAV paths
    if epub_dir:
        epub_base = Path(epub_dir)
        for name in ["nav.xhtml", "OEBPS/nav.xhtml", "toc.xhtml", "OEBPS/toc.xhtml"]:
            candidate = epub_base / name
            if candidate.exists():
                return TocInfo(
                    toc_type="nav", toc_href=name, toc_path=candidate,
                    ncx_href=ncx_href, ncx_path=ncx_path,
                )

    return TocInfo(toc_type="unknown", ncx_href=ncx_href, ncx_path=ncx_path)


def _build_toc_info(
    toc_type: str, href: str, opf_dir: Path, epub_dir: str | None
) -> TocInfo:
    """Build TocInfo, resolving absolute path if epub_dir is provided."""
    toc_path = None
    if epub_dir:
        resolved = (opf_dir / href).resolve()
        if resolved.exists():
            toc_path = resolved
    return TocInfo(toc_type=toc_type, toc_href=href, toc_path=toc_path)
