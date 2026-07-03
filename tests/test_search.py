"""Tests for BM25 search + SQLite inverted index (al_warraq.search)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from al_warraq import build_search_index, search, tokenize

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
    '<item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>'
    '</manifest>'
    '<spine toc="ncx"><itemref idref="c1"/><itemref idref="c2"/></spine>'
    '</package>'
)
_NCX = (
    '<?xml version="1.0"?>'
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
    '<docTitle><text>Test Book</text></docTitle><navMap>'
    '<navPoint id="n1" playOrder="1"><navLabel><text>Chapter One</text></navLabel>'
    '<content src="ch1.xhtml#c1"/>'
    '<navPoint id="n1a" playOrder="2"><navLabel><text>Redux Section</text></navLabel>'
    '<content src="ch1.xhtml#sec"/></navPoint></navPoint>'
    '<navPoint id="n2" playOrder="3"><navLabel><text>Chapter Two</text></navLabel>'
    '<content src="ch2.xhtml#c2"/></navPoint>'
    '</navMap></ncx>'
)
_CH1 = (
    '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
    '<h1 id="c1">Chapter One</h1>'
    '<p>An introduction with no special keywords here.</p>'
    '<h2 id="sec">Redux Section</h2>'
    '<p>Redux manages global state. Redux redux redux state management '
    'with the _app.js entry point.</p>'
    '</body></html>'
)
_CH2 = (
    '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
    '<h1 id="c2">Chapter Two</h1>'
    '<p>This chapter is about testing and deployment, nothing else.</p>'
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
        zf.writestr("OEBPS/ch2.xhtml", _CH2)
    return epub


def test_tokenize_preserves_tech_tokens() -> None:
    toks = tokenize("Using _app.js with Next.js")
    assert "_app.js" in toks
    assert "next.js" in toks
    assert toks == [t.lower() for t in toks]


def test_search_ranks_relevant_section_first(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    hits = search(str(epub), "redux state", output_dir=str(tmp_path / "out"))
    assert hits, "expected at least one hit"
    assert hits[0].breadcrumb[-1] == "Redux Section"
    assert hits[0].anchor == "sec"


def test_search_tech_token(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    hits = search(str(epub), "_app.js", output_dir=str(tmp_path / "out"))
    assert hits
    assert hits[0].breadcrumb[-1] == "Redux Section"


def test_no_match_returns_empty(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    assert search(str(epub), "nonexistentterm", output_dir=str(tmp_path / "out")) == []


def test_index_is_built_and_reused(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    out = str(tmp_path / "out")
    db1 = build_search_index(str(epub), out)
    assert db1.exists()
    mtime = db1.stat().st_mtime
    db2 = build_search_index(str(epub), out)  # should reuse, not rebuild
    assert db2 == db1
    assert db2.stat().st_mtime == mtime


def test_with_content_populates_body(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    out = str(tmp_path / "out")
    hits = search(str(epub), "redux state", with_content=True, output_dir=out)
    assert hits
    assert hits[0].content
    assert "Redux" in hits[0].content


def test_content_format_html_vs_plaintext(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    out = str(tmp_path / "out")
    html_hits = search(
        str(epub), "redux state", with_content=True,
        content_format="html", output_dir=out,
    )
    text_hits = search(
        str(epub), "redux state", with_content=True,
        content_format="plaintext", output_dir=out,
    )
    assert "<" in html_hits[0].content  # raw HTML has tags
    assert "<" not in text_hits[0].content  # plaintext stripped


def test_no_content_when_flag_off(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    hits = search(str(epub), "redux state", output_dir=str(tmp_path / "out"))
    assert hits[0].content is None


def test_chapter_rollup_groups_sections(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    out = str(tmp_path / "out")
    section_hits = search(str(epub), "redux state", group="section", output_dir=out)
    chapter_hits = search(str(epub), "redux state", group="chapter", output_dir=out)
    # Two ch1 sections match; rollup collapses them under one chapter.
    assert len(chapter_hits) < len(section_hits)
    assert chapter_hits[0].breadcrumb == ["Chapter One"]
    assert chapter_hits[0].n_sections >= 2
