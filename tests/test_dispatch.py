"""Tests for CLI invocation dispatch (path mode vs verb mode vs bare)."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest
from al_warraq.cli import _resolve_invocation, cli_entry

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
    '<h1 id="c1">Chapter One</h1><p>Some content.</p>'
    '</body></html>'
)


def _make_epub(tmp_path: Path) -> Path:
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", _CONTAINER)
        zf.writestr("OEBPS/content.opf", _OPF)
        zf.writestr("OEBPS/toc.ncx", _NCX)
        zf.writestr("OEBPS/ch1.xhtml", _CH1)
    return epub


# ------------------------------------------------------- _resolve_invocation


def test_path_only_resolves_to_path(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    assert _resolve_invocation([str(epub)]) == epub


def test_verb_plus_path_is_none(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    assert _resolve_invocation(["inspect", str(epub)]) is None


def test_bare_invocation_is_none() -> None:
    assert _resolve_invocation([]) is None


def test_flags_are_none() -> None:
    assert _resolve_invocation(["--help"]) is None
    assert _resolve_invocation(["-V"]) is None
    assert _resolve_invocation(["--version"]) is None


def test_command_name_is_none_even_if_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "inspect").write_text("not an epub")
    monkeypatch.chdir(tmp_path)
    assert _resolve_invocation(["inspect"]) is None


def test_existing_file_named_like_verb_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "inspect.epub").write_text("stub")
    monkeypatch.chdir(tmp_path)
    assert _resolve_invocation(["inspect.epub"]) == Path("inspect.epub")


def test_nonexistent_non_epub_is_none() -> None:
    assert _resolve_invocation(["no-such-thing"]) is None


def test_nonexistent_epub_resolves() -> None:
    assert _resolve_invocation(["missing.epub"]) == Path("missing.epub")


# ------------------------------------------------------------ path-mode runs


def _set_tty(monkeypatch: pytest.MonkeyPatch, value: bool) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: value)
    monkeypatch.setattr("sys.stdout.isatty", lambda: value)


def test_no_tty_falls_back_to_inspect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    epub = _make_epub(tmp_path)
    _set_tty(monkeypatch, False)
    monkeypatch.setattr("sys.argv", ["al-warraq", str(epub)])

    with pytest.raises(SystemExit) as exc:
        cli_entry()

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Test Book" in captured.out
    assert "tui" not in captured.err


def test_no_textual_hints_then_inspects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    epub = _make_epub(tmp_path)
    _set_tty(monkeypatch, True)
    monkeypatch.setattr("sys.argv", ["al-warraq", str(epub)])
    monkeypatch.setattr(importlib.util, "find_spec", lambda _name: None)

    with pytest.raises(SystemExit) as exc:
        cli_entry()

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "pip install al-warraq[tui]" in captured.err
    assert "Test Book" in captured.out


def test_path_mode_invalid_epub_exits_1(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = tmp_path / "broken.epub"
    bad.write_text("not a zip at all")
    _set_tty(monkeypatch, True)
    monkeypatch.setattr("sys.argv", ["al-warraq", str(bad)])
    monkeypatch.setattr(importlib.util, "find_spec", lambda _name: object())

    with pytest.raises(SystemExit) as exc:
        cli_entry()

    assert exc.value.code == 1
    assert "Error:" in capsys.readouterr().err
