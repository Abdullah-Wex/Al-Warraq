"""Tests for local + MinIO extraction caches in ``extract_epub``."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from epubsage import epub as epub_mod
from epubsage.epub import extract_epub, hash_epub


def _make_minimal_epub(tmp_path: Path) -> Path:
    """Build a tiny valid zip that passes the zip-bomb / zip-slip checks."""
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("OEBPS/content.opf", "<package version='3.0'/>")
    return epub


def test_local_cache_hit_skips_extraction(tmp_path: Path) -> None:
    epub = _make_minimal_epub(tmp_path)
    out = tmp_path / "out"
    file_hash = hash_epub(str(epub))

    # Pre-seed a non-empty extraction dir.
    target = out / file_hash
    target.mkdir(parents=True)
    (target / "marker").write_text("kept")

    with patch.object(epub_mod.zipfile, "ZipFile") as zf_mock:
        result = extract_epub(str(epub), str(out))

    assert result == target
    zf_mock.assert_not_called()
    assert (target / "marker").read_text() == "kept"


def test_local_cache_empty_dir_triggers_extraction(tmp_path: Path) -> None:
    epub = _make_minimal_epub(tmp_path)
    out = tmp_path / "out"
    file_hash = hash_epub(str(epub))
    (out / file_hash).mkdir(parents=True)  # empty

    result = extract_epub(str(epub), str(out))

    assert result == out / file_hash
    assert (out / file_hash / "mimetype").exists()


def test_minio_hit_downloads_and_skips_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    epub = _make_minimal_epub(tmp_path)
    out = tmp_path / "out"

    cache = MagicMock()
    cache.has.return_value = True

    def _fake_download(file_hash: str, local_dir: Path) -> None:
        (Path(local_dir) / file_hash).mkdir(parents=True, exist_ok=True)
        (Path(local_dir) / file_hash / "from_minio").write_text("ok")

    cache.download.side_effect = _fake_download
    monkeypatch.setattr(epub_mod, "get_minio_cache", lambda: cache)

    with patch.object(epub_mod.zipfile, "ZipFile") as zf_mock:
        result = extract_epub(str(epub), str(out))

    zf_mock.assert_not_called()
    cache.download.assert_called_once()
    cache.upload.assert_not_called()
    assert (result / "from_minio").exists()


def test_minio_miss_uploads_after_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    epub = _make_minimal_epub(tmp_path)
    out = tmp_path / "out"

    cache = MagicMock()
    cache.has.return_value = False
    monkeypatch.setattr(epub_mod, "get_minio_cache", lambda: cache)

    result = extract_epub(str(epub), str(out))

    assert (result / "mimetype").exists()
    cache.upload.assert_called_once()
    cache.download.assert_not_called()


def test_no_cache_fresh_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    epub = _make_minimal_epub(tmp_path)
    out = tmp_path / "out"
    monkeypatch.setattr(epub_mod, "get_minio_cache", lambda: None)

    result = extract_epub(str(epub), str(out))

    assert (result / "mimetype").exists()
