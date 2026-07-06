"""Pilot tests for the interactive app (skipped when textual isn't installed)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

textual = pytest.importorskip("textual")

from al_warraq import Book  # noqa: E402
from al_warraq.tui.app import WarraqApp  # noqa: E402
from al_warraq.tui.widgets import CommandPopup  # noqa: E402
from textual.widgets import Input, RichLog, Static  # noqa: E402

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


def _log_text(app: WarraqApp) -> str:
    log = app.query_one(RichLog)
    return "\n".join(strip.text for strip in log.lines)


async def test_header_shows_title_version_toc_type(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test():
        header = app.query_one("#header", Static)
        assert str(header.render()) == "Test Book · EPUB 2.0 · ncx"


async def test_slash_shows_popup_and_filters(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        popup = app.query_one(CommandPopup)
        assert popup.display is False
        await pilot.press("/")
        assert popup.display is True
        assert popup.option_count == 7
        await pilot.press("t")
        assert popup.option_count == 1
        assert popup.completion == "/toc"


async def test_tab_completes_highlighted_command(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        await pilot.press("/", "t", "tab")
        assert app.query_one(Input).value == "/toc "
        assert app.query_one(CommandPopup).display is False


async def test_bare_text_runs_search(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        await pilot.press(*"redux", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "result(s) for 'redux'" in _log_text(app)


async def test_toc_command_renders_tree(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        await pilot.press(*"/toc", "enter", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "Chapter One" in _log_text(app)


async def test_unknown_command_single_error_line(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        await pilot.press(*"/nope x", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "Unknown command: /nope" in _log_text(app)


async def test_quit_exits(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        await pilot.press(*"/quit", "enter", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert app.is_running is False


async def test_escape_clears_input_and_popup(tmp_path: Path) -> None:
    app = WarraqApp(_make_book(tmp_path))
    async with app.run_test() as pilot:
        await pilot.press("/", "t", "escape")
        assert app.query_one(Input).value == ""
        assert app.query_one(CommandPopup).display is False
