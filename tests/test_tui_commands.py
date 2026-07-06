"""Tests for the slash-command registry and dispatcher (no textual needed)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from al_warraq import Book
from al_warraq.tui.commands import COMMANDS, execute, match
from rich.console import Group
from rich.text import Text
from rich.tree import Tree

_CONTAINER = (
    '<?xml version="1.0"?>'
    '<container version="1.0" '
    'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    '<rootfiles><rootfile full-path="OEBPS/content.opf" '
    'media-type="application/oebps-package+xml"/></rootfiles></container>'
)
_OPF = (
    '<?xml version="1.0"?>'
    '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" '
    'unique-identifier="id">'
    '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<dc:title>Test Book</dc:title></metadata>'
    '<manifest>'
    '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
    '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
    '</manifest>'
    '<spine toc="ncx"><itemref idref="c1"/></spine>'
    '</package>'
)
_NCX = (
    '<?xml version="1.0"?>'
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
    '<docTitle><text>Test Book</text></docTitle><navMap>'
    '<navPoint id="n1" playOrder="1"><navLabel><text>Chapter One</text></navLabel>'
    '<content src="ch1.xhtml#c1"/></navPoint>'
    '</navMap></ncx>'
)
_CH1 = (
    '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
    '<h1 id="c1">Chapter One</h1>'
    '<p>Redux manages global state for the application.</p>'
    '</body></html>'
)


def _make_book(tmp_path: Path) -> Book:
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", _CONTAINER)
        zf.writestr("OEBPS/content.opf", _OPF)
        zf.writestr("OEBPS/toc.ncx", _NCX)
        zf.writestr("OEBPS/ch1.xhtml", _CH1)
    return Book.open(epub, str(tmp_path / "out"))


# ------------------------------------------------------------------- matching


def test_match_filters_by_prefix() -> None:
    assert [c.name for c in match("/t")] == ["/toc"]
    assert [c.name for c in match("/")] == [c.name for c in COMMANDS]
    assert match("/nope") == []


# ------------------------------------------------------------------ execution


def test_bare_text_runs_search(tmp_path: Path) -> None:
    book = _make_book(tmp_path)
    result = execute(book, "redux")
    assert isinstance(result, Group)


def test_search_without_query_is_usage_error(tmp_path: Path) -> None:
    result = execute(_make_book(tmp_path), "/search")
    assert isinstance(result, Text)
    assert result.plain.startswith("Error: Usage: /search")


def test_toc_returns_tree(tmp_path: Path) -> None:
    assert isinstance(execute(_make_book(tmp_path), "/toc"), Tree)


def test_info_returns_kv_block(tmp_path: Path) -> None:
    result = execute(_make_book(tmp_path), "/info")
    assert isinstance(result, Text)
    assert "Test Book" in result.plain


def test_content_by_anchor(tmp_path: Path) -> None:
    result = execute(_make_book(tmp_path), "/content c1")
    assert isinstance(result, Text)
    assert "Redux manages global state" in result.plain


def test_content_without_ref_is_usage_error(tmp_path: Path) -> None:
    result = execute(_make_book(tmp_path), "/content")
    assert isinstance(result, Text)
    assert result.plain.startswith("Error: Usage: /content")


def test_content_unknown_ref_is_single_error_line(tmp_path: Path) -> None:
    result = execute(_make_book(tmp_path), "/content nosuchanchor")
    assert isinstance(result, Text)
    assert result.plain.startswith("Error:")
    assert "\n" not in result.plain


def test_unknown_command_is_single_error_line(tmp_path: Path) -> None:
    result = execute(_make_book(tmp_path), "/frobnicate")
    assert isinstance(result, Text)
    assert result.plain == "Error: Unknown command: /frobnicate. Type /help for the list."


def test_quit_returns_none(tmp_path: Path) -> None:
    assert execute(_make_book(tmp_path), "/quit") is None
