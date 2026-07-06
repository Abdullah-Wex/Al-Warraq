"""Tests for output-dir resolution and MinIO cache factory."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from al_warraq.storage import get_minio_cache, resolve_output_dir, user_cache_dir


def test_resolve_output_dir_default_is_user_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AL_WARRAQ_OUTPUT_DIR", raising=False)
    assert resolve_output_dir() == str(user_cache_dir())


def test_user_cache_dir_is_persistent_and_named() -> None:
    path = user_cache_dir()
    assert path.name == "al-warraq"
    # Never inside the system tempdir — that's the whole point.
    import tempfile

    assert not str(path).startswith(tempfile.gettempdir())
    if sys.platform == "darwin":
        assert path == Path.home() / "Library" / "Caches" / "al-warraq"


def test_user_cache_dir_honors_xdg_on_linux(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert user_cache_dir() == tmp_path / "al-warraq"


def test_resolve_output_dir_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("AL_WARRAQ_OUTPUT_DIR", str(tmp_path))
    assert resolve_output_dir() == str(tmp_path)


def test_resolve_output_dir_empty_env_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AL_WARRAQ_OUTPUT_DIR", "")
    assert resolve_output_dir() == str(user_cache_dir())


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
