"""Tests for process_epub: contract, determinism, injection, defaults, errors."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Sequence
from pathlib import Path

import pytest
from al_warraq.content_store import LocalContentStore, sha256_hex
from al_warraq.exceptions import BlobNotFoundError, InvalidEpubError
from al_warraq.hooks import StructuralSplitter
from al_warraq.processing import SCHEMA_VERSION, process_epub

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
    '<dc:title>Test Book</dc:title>'
    '<dc:creator>An Author</dc:creator>'
    '<dc:publisher>A Publisher</dc:publisher></metadata>'
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
    '<navPoint id="n1a" playOrder="2"><navLabel><text>First Section</text></navLabel>'
    '<content src="ch1.xhtml#sec"/></navPoint></navPoint>'
    '<navPoint id="n2" playOrder="3"><navLabel><text>Chapter Two</text></navLabel>'
    '<content src="ch2.xhtml#c2"/></navPoint>'
    '</navMap></ncx>'
)
_CH1 = (
    '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
    '<h1 id="c1">Chapter One</h1>'
    '<p>An opening paragraph about state management.</p>'
    '<h2 id="sec">First Section</h2>'
    '<p>Redux manages global state for the application.</p>'
    '</body></html>'
)
_CH2 = (
    '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
    '<h1 id="c2">Chapter Two</h1>'
    '<p>This chapter is about testing and deployment.</p>'
    '</body></html>'
)


def _epub_bytes(tmp_path: Path) -> bytes:
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", _CONTAINER)
        zf.writestr("OEBPS/content.opf", _OPF)
        zf.writestr("OEBPS/toc.ncx", _NCX)
        zf.writestr("OEBPS/ch1.xhtml", _CH1)
        zf.writestr("OEBPS/ch2.xhtml", _CH2)
    return epub.read_bytes()


@pytest.fixture
def stored(tmp_path: Path) -> tuple[str, LocalContentStore, str]:
    """A stored test EPUB: (content_hash, store, extraction output_dir)."""
    store = LocalContentStore(tmp_path / "store")
    content_hash = store.put(_epub_bytes(tmp_path))
    return content_hash, store, str(tmp_path / "out")


class _FixedSplitter:
    """Fake PassageSplitter: always the same two passages."""

    def split(self, _chapter_text: str) -> list[str]:
        return ["first passage", "second passage"]


class _FixedEmbedder:
    """Fake Embedder: a constant two-dimensional vector per passage."""

    def embed(self, passages: Sequence[str]) -> list[list[float]]:
        return [[0.0, 1.0] for _ in passages]


# ------------------------------------------------------------ output contract


def test_output_contract(stored: tuple[str, LocalContentStore, str]) -> None:
    content_hash, store, out = stored
    result = process_epub(content_hash, store, output_dir=out)

    assert result.schema_version == SCHEMA_VERSION
    assert result.content_hash == content_hash
    assert result.metadata.title == "Test Book"
    assert result.metadata.creator == "An Author"
    assert result.metadata.publisher == "A Publisher"
    assert result.metadata.epub_version == "2.0"
    assert result.metadata.toc_type == "ncx"

    assert [c.title for c in result.chapters] == ["Chapter One", "Chapter Two"]
    assert [c.index for c in result.chapters] == [0, 1]
    # A chapter's text includes its subsections'.
    assert "Redux manages global state" in result.chapters[0].text

    assert result.passages, "non-empty book must yield passages"
    first = result.passages[0]
    assert first.passage_id == f"{content_hash[:16]}-c000-p0000"
    assert first.content_hash == content_hash
    assert first.chapter_index == 0
    assert first.position == 0
    assert first.char_start is not None
    assert first.char_end is not None
    chapter_text = result.chapters[0].text
    assert chapter_text[first.char_start:first.char_end] == first.text


def test_deterministic_output(stored: tuple[str, LocalContentStore, str]) -> None:
    content_hash, store, out = stored
    first = process_epub(content_hash, store, output_dir=out)
    # Second run reuses the extraction cache — output must be identical.
    second = process_epub(content_hash, store, output_dir=out)

    as_json = [json.dumps(r.to_dict(), sort_keys=True) for r in (first, second)]
    assert as_json[0] == as_json[1]


# ---------------------------------------------------------- strategy injection


def test_injected_splitter_is_used(stored: tuple[str, LocalContentStore, str]) -> None:
    content_hash, store, out = stored
    result = process_epub(
        content_hash, store, splitter=_FixedSplitter(), output_dir=out,
    )

    chapter_zero = [p for p in result.passages if p.chapter_index == 0]
    assert [p.text for p in chapter_zero] == ["first passage", "second passage"]
    assert [p.position for p in chapter_zero] == [0, 1]
    # The fake's passages don't occur in the chapter text: offsets are None.
    assert chapter_zero[0].char_start is None


def test_injected_embedder_attaches_vectors(
    stored: tuple[str, LocalContentStore, str],
) -> None:
    content_hash, store, out = stored
    result = process_epub(
        content_hash, store, embedder=_FixedEmbedder(), output_dir=out,
    )

    assert result.passages
    assert all(p.vector == [0.0, 1.0] for p in result.passages)


# ----------------------------------------------------------------- defaults


def test_default_no_embedder_means_no_vectors(
    stored: tuple[str, LocalContentStore, str],
) -> None:
    content_hash, store, out = stored
    result = process_epub(content_hash, store, output_dir=out)
    assert all(p.vector is None for p in result.passages)


def test_structural_splitter_groups_paragraphs() -> None:
    splitter = StructuralSplitter(max_chars=30)
    text = "one one one\n\ntwo two two\n\nthree three three"

    passages = splitter.split(text)

    assert passages == ["one one one\n\ntwo two two", "three three three"]


def test_structural_splitter_never_splits_a_paragraph() -> None:
    long_paragraph = "word " * 100
    passages = StructuralSplitter(max_chars=10).split(long_paragraph)
    assert len(passages) == 1


def test_structural_splitter_empty_text_yields_nothing() -> None:
    assert StructuralSplitter().split("") == []
    assert StructuralSplitter().split("\n\n \n\n") == []


# ------------------------------------------------------------------- errors


def test_unknown_hash_raises_blob_not_found(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path / "store")
    with pytest.raises(BlobNotFoundError):
        process_epub(sha256_hex(b"never stored"), store, output_dir=str(tmp_path))


def test_malformed_hash_raises_value_error(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path / "store")
    with pytest.raises(ValueError, match="content_hash"):
        process_epub("not-a-hash", store, output_dir=str(tmp_path))


def test_tampered_blob_raises_invalid_epub(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path / "store")
    # Plant bytes under a hash they don't match.
    wrong_hash = sha256_hex(b"the original bytes")
    (tmp_path / "store" / wrong_hash).write_bytes(b"tampered bytes")

    with pytest.raises(InvalidEpubError, match="content hash"):
        process_epub(wrong_hash, store, output_dir=str(tmp_path / "out"))
