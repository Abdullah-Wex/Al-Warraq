"""Pilot tests for the library view (skipped when textual isn't installed)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

textual = pytest.importorskip("textual")

from al_warraq.tui.app import BookScreen  # noqa: E402
from al_warraq.tui.library import LibraryApp, LibraryScreen  # noqa: E402
from textual.widgets import Input, OptionList, Static  # noqa: E402

_CONTAINER = (
    '<?xml version="1.0"?>'
    '<container version="1.0" '
    'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    '<rootfiles><rootfile full-path="OEBPS/content.opf" '
    'media-type="application/oebps-package+xml"/></rootfiles></container>'
)


def _opf(title: str) -> str:
    return (
        '<?xml version="1.0"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" '
        'unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{title}</dc:title></metadata>"
        '<manifest>'
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
        '</manifest>'
        '<spine toc="ncx"><itemref idref="c1"/></spine>'
        '</package>'
    )


def _ncx(title: str) -> str:
    return (
        '<?xml version="1.0"?>'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f"<docTitle><text>{title}</text></docTitle><navMap>"
        '<navPoint id="n1" playOrder="1"><navLabel><text>Chapter One</text></navLabel>'
        '<content src="ch1.xhtml#c1"/></navPoint>'
        '</navMap></ncx>'
    )


def _chapter(body: str) -> str:
    return (
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        f'<h1 id="c1">Chapter One</h1><p>{body}</p>'
        '</body></html>'
    )


def _make_library(tmp_path: Path) -> Path:
    """Two small books with distinct titles and contents."""
    library = tmp_path / "books"
    library.mkdir()
    for name, title, body in [
        ("alpha.epub", "Alpha Book", "Redux manages global state."),
        ("beta.epub", "Beta Book", "Kubernetes orchestrates containers."),
    ]:
        with zipfile.ZipFile(library / name, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr("META-INF/container.xml", _CONTAINER)
            zf.writestr("OEBPS/content.opf", _opf(title))
            zf.writestr("OEBPS/toc.ncx", _ncx(title))
            zf.writestr("OEBPS/ch1.xhtml", _chapter(body))
    return library


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AL_WARRAQ_OUTPUT_DIR", str(tmp_path / "cache"))


async def test_picker_lists_books_with_titles(tmp_path: Path) -> None:
    app = LibraryApp(_make_library(tmp_path))
    async with app.run_test() as pilot:
        options = app.query_one(OptionList)
        assert options.option_count == 2
        await app.workers.wait_for_complete()
        await pilot.pause()
        labels = [
            str(options.get_option_at_index(i).prompt)
            for i in range(options.option_count)
        ]
        assert any("Alpha Book" in label for label in labels)
        assert any("Beta Book" in label for label in labels)
        assert "book(s)" in str(app.query_one("#header", Static).render())


async def test_selecting_a_book_opens_its_session(tmp_path: Path) -> None:
    app = LibraryApp(_make_library(tmp_path))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("enter")  # first book highlighted by default
        await pilot.pause()
        assert isinstance(app.screen, BookScreen)
        assert "Alpha Book" in str(app.screen.query_one("#header", Static).render())


async def test_escape_returns_to_picker(tmp_path: Path) -> None:
    app = LibraryApp(_make_library(tmp_path))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, BookScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, LibraryScreen)


async def test_search_merges_results_across_books(tmp_path: Path) -> None:
    app = LibraryApp(_make_library(tmp_path))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        app.query_one(Input).focus()
        await pilot.press(*"kubernetes", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        options = app.query_one(OptionList)
        labels = [
            str(options.get_option_at_index(i).prompt)
            for i in range(options.option_count)
        ]
        assert any("Beta Book" in label for label in labels)

        # Opening the top hit jumps into that book's session at the section.
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, BookScreen)
        assert app.screen.initial_command is not None
        assert app.screen.initial_command.startswith("/content")


async def test_search_no_matches_shows_notice(tmp_path: Path) -> None:
    app = LibraryApp(_make_library(tmp_path))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        app.query_one(Input).focus()
        await pilot.press(*"zzzznothing", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        options = app.query_one(OptionList)
        assert "No matches" in str(options.get_option_at_index(0).prompt)
