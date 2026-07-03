"""NCX parsing — docTitle and navMap extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .exceptions import InvalidEpubError

NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"


@dataclass
class NavPoint:
    """A single navigation point from the NCX navMap."""

    id: str
    label: str
    src: str
    file: str
    anchor: str | None
    children: list[NavPoint] = field(default_factory=list)
    play_order: int | None = None
    class_name: str | None = None
    nav_type: str | None = None
    abs_file: str | None = None


@dataclass
class NcxData:
    """Parsed NCX file data."""

    doc_title: str | None
    nav_points: list[NavPoint]


def parse_ncx(ncx_path: str) -> NcxData:
    """Parse an NCX file for docTitle and navMap structure."""
    try:
        tree = ET.parse(ncx_path)  # noqa: S314
    except ET.ParseError as e:
        raise InvalidEpubError(f"Failed to parse NCX as XML: {e}") from e

    root = tree.getroot()
    base = Path(ncx_path).parent

    # docTitle
    doc_title = _find_text(root, "docTitle/text")

    # navMap
    nav_map = _find(root, "navMap")
    if nav_map is None:
        return NcxData(doc_title=doc_title, nav_points=[])

    nav_points = _parse_nav_points(nav_map, base)
    return NcxData(doc_title=doc_title, nav_points=nav_points)


def _parse_nav_points(parent: ET.Element, base: Path) -> list[NavPoint]:
    """Parse navPoint children in document order (no sorting)."""
    points: list[NavPoint] = []

    for el in _findall(parent, "navPoint"):
        np_id = el.get("id", "")
        class_name = el.get("class")

        play_order_str = el.get("playOrder")
        play_order = int(play_order_str) if play_order_str else None

        label = _find_text(el, "navLabel/text") or ""

        content_el = _find(el, "content")
        src = content_el.get("src", "") if content_el is not None else ""

        # Split src into file and anchor
        if "#" in src:
            file_path, anchor = src.split("#", 1)
        else:
            file_path = src
            anchor = None

        abs_file = str((base / file_path).resolve()) if file_path else None

        children = _parse_nav_points(el, base)

        points.append(NavPoint(
            id=np_id,
            label=label,
            src=src,
            file=file_path,
            anchor=anchor,
            children=children,
            play_order=play_order,
            class_name=class_name,
            abs_file=abs_file,
        ))

    return points


def _find(parent: ET.Element, tag: str) -> ET.Element | None:
    """Find element with NCX namespace, fallback to no namespace."""
    # Build namespaced path
    parts = tag.split("/")
    ns_path = "/".join(f"{{{NCX_NS}}}{p}" for p in parts)
    el = parent.find(ns_path)
    if el is not None:
        return el
    return parent.find(tag)


def _findall(parent: ET.Element, tag: str) -> list[ET.Element]:
    """Find all direct children matching tag, with namespace fallback."""
    items = parent.findall(f"{{{NCX_NS}}}{tag}")
    if items:
        return items
    return parent.findall(tag)


def _find_text(parent: ET.Element, path: str) -> str | None:
    """Find element by path and return its stripped text, or None."""
    el = _find(parent, path)
    if el is not None and el.text:
        return el.text.strip()
    return None
