"""NAV (XHTML) TOC parsing — EPUB 3 navigation document."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .exceptions import InvalidEpubError
from .ncx import NavPoint

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"


def parse_nav(nav_path: str) -> list[NavPoint]:
    """Parse NAV XHTML for TOC entries. Returns list[NavPoint]."""
    try:
        tree = ET.parse(nav_path)  # noqa: S314
    except ET.ParseError as e:
        raise InvalidEpubError(f"Failed to parse NAV as XML: {e}") from e

    root = tree.getroot()
    base = Path(nav_path).parent

    toc_nav = _find_toc_nav(root)
    if toc_nav is None:
        return []

    ol = _find_ol(toc_nav)
    if ol is None:
        return []

    return _parse_items(ol, counter=[0], base=base)


def _find_toc_nav(root: ET.Element) -> ET.Element | None:
    """Find <nav epub:type='toc'> element."""
    for tag in [f"{{{XHTML_NS}}}nav", "nav"]:
        for nav in root.iter(tag):
            epub_type = nav.get(f"{{{EPUB_NS}}}type") or nav.get("epub:type") or ""
            if "toc" in epub_type:
                return nav
    return None


def _find_ol(parent: ET.Element) -> ET.Element | None:
    """Find first <ol> descendant (namespaced or not)."""
    for tag in [f"{{{XHTML_NS}}}ol", "ol"]:
        ol = parent.find(f".//{tag}")
        if ol is not None:
            return ol
    return None


def _parse_items(
    ol: ET.Element, counter: list[int], base: Path,
) -> list[NavPoint]:
    """Recursively parse <li> items from an <ol>."""
    points: list[NavPoint] = []

    for li in _findall_li(ol):
        a = _find_a(li)
        if a is None:
            continue

        counter[0] += 1

        href = a.get("href", "")
        label = "".join(a.itertext()).strip()

        if "#" in href:
            file_path, anchor = href.split("#", 1)
        else:
            file_path = href
            anchor = None

        abs_file = str((base / file_path).resolve()) if file_path else None

        children_ol = _find_direct_ol(li)
        children = (
            _parse_items(children_ol, counter, base) if children_ol else []
        )

        points.append(NavPoint(
            id=f"nav-{counter[0]}",
            label=label,
            src=href,
            file=file_path,
            anchor=anchor,
            children=children,
            play_order=counter[0],
            class_name=None,
            abs_file=abs_file,
        ))

    return points


def _findall_li(ol: ET.Element) -> list[ET.Element]:
    """Find all direct <li> children with namespace fallback."""
    items = ol.findall(f"{{{XHTML_NS}}}li")
    if items:
        return items
    return ol.findall("li")


def _find_a(li: ET.Element) -> ET.Element | None:
    """Find first <a> child with namespace fallback."""
    a = li.find(f"{{{XHTML_NS}}}a")
    if a is not None:
        return a
    return li.find("a")


def _find_direct_ol(li: ET.Element) -> ET.Element | None:
    """Find direct <ol> child of <li> with namespace fallback."""
    ol = li.find(f"{{{XHTML_NS}}}ol")
    if ol is not None:
        return ol
    return li.find("ol")
