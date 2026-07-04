"""Tests for the Book facade — the high-level API every frontend shares."""

from __future__ import annotations

from pathlib import Path

import pytest
from al_warraq import Book, SectionNotFoundError

from tests.test_search import _make_epub


def _open(tmp_path: Path) -> Book:
    return Book.open(_make_epub(tmp_path), output_dir=str(tmp_path / "out"))


def test_open_exposes_basics(tmp_path: Path) -> None:
    book = _open(tmp_path)
    assert book.title == "Test Book"
    assert book.version == "2.0"
    assert book.toc_type == "ncx"
    assert len(book.hash) == 16


def test_doc_title_prefers_toc_title(tmp_path: Path) -> None:
    book = _open(tmp_path)
    assert book.doc_title == "Test Book"


def test_toc_is_classified_and_cached(tmp_path: Path) -> None:
    book = _open(tmp_path)
    tree = book.toc()
    labels = [pt.label for pt in tree]
    assert "Chapter One" in labels
    assert all(pt.nav_type is not None for pt in tree)
    assert book.toc() is tree  # cached, not re-parsed


def test_flat_toc_includes_nested_entries(tmp_path: Path) -> None:
    book = _open(tmp_path)
    labels = [pt.label for pt in book.flat_toc()]
    assert "Redux Section" in labels  # nested under Chapter One


def test_search_returns_ranked_hits(tmp_path: Path) -> None:
    book = _open(tmp_path)
    hits = book.search("redux state")
    assert hits
    assert hits[0].anchor == "sec"


def test_section_by_anchor(tmp_path: Path) -> None:
    book = _open(tmp_path)
    section = book.section(anchor="sec", output_format="plaintext")
    assert section.anchor == "sec"
    assert section.file == "ch1.xhtml"
    assert section.output_format == "plaintext"
    assert "Redux manages global state" in section.text


def test_section_by_file(tmp_path: Path) -> None:
    book = _open(tmp_path)
    section = book.section(file="ch2.xhtml", output_format="plaintext")
    assert "testing and deployment" in section.text


def test_section_unknown_anchor_raises(tmp_path: Path) -> None:
    book = _open(tmp_path)
    with pytest.raises(SectionNotFoundError, match="nope"):
        book.section(anchor="nope")


def test_section_unknown_file_raises(tmp_path: Path) -> None:
    book = _open(tmp_path)
    with pytest.raises(SectionNotFoundError, match=r"ghost\.xhtml"):
        book.section(file="ghost.xhtml")


def test_section_without_target_raises(tmp_path: Path) -> None:
    book = _open(tmp_path)
    with pytest.raises(ValueError, match="anchor or a file"):
        book.section()
