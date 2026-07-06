"""Tests for book discovery, unzipped-package support, and directory dispatch."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from al_warraq import Book
from al_warraq.cli import _resolve_invocation, cli_entry
from al_warraq.epub import hash_epub, is_epub_package
from al_warraq.library import find_books

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

_FILES = {
    "mimetype": "application/epub+zip",
    "META-INF/container.xml": _CONTAINER,
    "OEBPS/content.opf": _OPF,
    "OEBPS/toc.ncx": _NCX,
    "OEBPS/ch1.xhtml": _CH1,
}


def _make_epub_file(directory: Path, name: str = "zipped.epub") -> Path:
    epub = directory / name
    with zipfile.ZipFile(epub, "w") as zf:
        for rel, content in _FILES.items():
            zf.writestr(rel, content)
    return epub


def _make_epub_package(directory: Path, name: str = "unzipped.epub") -> Path:
    package = directory / name
    for rel, content in _FILES.items():
        target = package / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return package


# ------------------------------------------------------------------ discovery


def test_find_books_files_and_packages(tmp_path: Path) -> None:
    file_book = _make_epub_file(tmp_path)
    package = _make_epub_package(tmp_path)
    (tmp_path / "notes.txt").write_text("not a book")
    (tmp_path / "random-folder").mkdir()

    assert find_books(tmp_path) == [package, file_book]  # sorted by name


def test_find_books_skips_icloud_placeholders(tmp_path: Path) -> None:
    (tmp_path / ".book.epub.icloud").write_text("stub")
    assert find_books(tmp_path) == []


def test_is_epub_package(tmp_path: Path) -> None:
    package = _make_epub_package(tmp_path)
    assert is_epub_package(package)
    assert not is_epub_package(tmp_path / "nope")
    assert not is_epub_package(_make_epub_file(tmp_path))  # file, not dir


# --------------------------------------------------------- unzipped packages


def test_hash_epub_on_package_is_deterministic(tmp_path: Path) -> None:
    package = _make_epub_package(tmp_path)
    first = hash_epub(str(package))
    assert first == hash_epub(str(package))
    assert len(first) == 16

    (package / "OEBPS" / "ch1.xhtml").write_text(_CH1 + "<!-- changed -->")
    assert hash_epub(str(package)) != first


def test_book_open_on_package_parses_in_place(tmp_path: Path) -> None:
    package = _make_epub_package(tmp_path)
    book = Book.open(package, str(tmp_path / "out"))
    assert book.title == "Test Book"
    assert book.version == "2.0"
    assert [pt.label for pt in book.flat_toc()] == ["Chapter One"]
    hits = book.search("redux")
    assert hits and hits[0].anchor == "c1"


# ------------------------------------------------------------------ dispatch


def test_directory_resolves_to_path_mode(tmp_path: Path) -> None:
    assert _resolve_invocation([str(tmp_path)]) == tmp_path


def _set_no_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)


def test_directory_no_tty_prints_listing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _make_epub_file(tmp_path)
    _make_epub_package(tmp_path)
    _set_no_tty(monkeypatch)
    monkeypatch.setattr("sys.argv", ["al-warraq", str(tmp_path)])
    monkeypatch.setenv("AL_WARRAQ_OUTPUT_DIR", str(tmp_path / "out"))

    cli_entry()

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        path, title, version = line.split("\t")
        assert path.endswith(".epub")
        assert title == "Test Book"
        assert version == "EPUB 2.0"


def test_empty_directory_fails_with_exit_1(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_no_tty(monkeypatch)
    monkeypatch.setattr("sys.argv", ["al-warraq", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        cli_entry()

    assert exc.value.code == 1
    assert "No EPUB books found" in capsys.readouterr().err


def test_epub_package_dir_routes_to_single_book(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = _make_epub_package(tmp_path)
    _set_no_tty(monkeypatch)
    monkeypatch.setattr("sys.argv", ["al-warraq", str(package)])
    monkeypatch.setenv("AL_WARRAQ_OUTPUT_DIR", str(tmp_path / "out"))

    with pytest.raises(SystemExit) as exc:
        cli_entry()

    assert exc.value.code == 0
    assert "Test Book" in capsys.readouterr().out
