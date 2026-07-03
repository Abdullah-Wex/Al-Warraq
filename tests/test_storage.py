"""Tests for output-dir resolution and MinIO cache factory."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest
from epubsage.storage import get_minio_cache, resolve_output_dir


def test_resolve_output_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EPUBSAGE_OUTPUT_DIR", raising=False)
    expected = str(Path(tempfile.gettempdir()) / "epubsage")
    assert resolve_output_dir() == expected


def test_resolve_output_dir_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("EPUBSAGE_OUTPUT_DIR", str(tmp_path))
    assert resolve_output_dir() == str(tmp_path)


def test_resolve_output_dir_empty_env_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EPUBSAGE_OUTPUT_DIR", "")
    expected = str(Path(tempfile.gettempdir()) / "epubsage")
    assert resolve_output_dir() == expected


def test_get_minio_cache_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET"):
        monkeypatch.delenv(k, raising=False)
    assert get_minio_cache() is None


def test_get_minio_cache_partial_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)
    assert get_minio_cache() is None


def test_get_minio_cache_without_minio_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.setenv("MINIO_SECRET_KEY", "s")
    monkeypatch.setenv("MINIO_BUCKET", "b")
    monkeypatch.setitem(sys.modules, "minio", None)
    assert get_minio_cache() is None
