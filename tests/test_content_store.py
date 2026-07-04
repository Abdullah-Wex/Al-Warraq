"""Tests for the content-addressed, deduplicated ContentStore backends."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from al_warraq.content_store import (
    ContentStore,
    LocalContentStore,
    MinioContentStore,
    get_minio_content_store,
    is_content_hash,
    sha256_hex,
)
from al_warraq.exceptions import BlobNotFoundError

_DATA = b"epub bytes here"


# ----------------------------------------------------------- LocalContentStore


def test_put_returns_full_sha256(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path)
    content_hash = store.put(_DATA)
    assert content_hash == sha256_hex(_DATA)
    assert is_content_hash(content_hash)
    assert (tmp_path / content_hash).read_bytes() == _DATA


def test_put_same_bytes_twice_stores_one_blob(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path)
    first = store.put(_DATA)
    mtime = (tmp_path / first).stat().st_mtime_ns

    second = store.put(_DATA)

    assert second == first
    assert len(list(tmp_path.iterdir())) == 1
    # No second write: the blob file was left untouched.
    assert (tmp_path / first).stat().st_mtime_ns == mtime


def test_exists_get_delete_round_trip(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path)
    content_hash = store.put(_DATA)

    assert store.exists(content_hash) is True
    assert store.get(content_hash) == _DATA

    store.delete(content_hash)
    assert store.exists(content_hash) is False


def test_get_unknown_hash_raises(tmp_path: Path) -> None:
    store = LocalContentStore(tmp_path)
    with pytest.raises(BlobNotFoundError):
        store.get(sha256_hex(b"never stored"))


def test_local_store_satisfies_protocol(tmp_path: Path) -> None:
    assert isinstance(LocalContentStore(tmp_path), ContentStore)


# ----------------------------------------------------------- MinioContentStore


class _FakeS3Error(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@pytest.fixture
def fake_minio(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Install a stub ``minio`` package and return the mocked client."""
    client = MagicMock()
    minio_mod = types.ModuleType("minio")
    minio_mod.Minio = MagicMock(return_value=client)  # type: ignore[attr-defined]
    error_mod = types.ModuleType("minio.error")
    error_mod.S3Error = _FakeS3Error  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "minio", minio_mod)
    monkeypatch.setitem(sys.modules, "minio.error", error_mod)
    return client


def _make_store() -> MinioContentStore:
    return MinioContentStore("host:9000", "key", "secret", "bucket")


def test_minio_put_skips_existing_blob(fake_minio: MagicMock) -> None:
    store = _make_store()
    fake_minio.stat_object.return_value = object()  # blob exists

    content_hash = store.put(_DATA)

    assert content_hash == sha256_hex(_DATA)
    fake_minio.put_object.assert_not_called()


def test_minio_put_writes_new_blob_under_prefix(fake_minio: MagicMock) -> None:
    store = _make_store()
    fake_minio.stat_object.side_effect = _FakeS3Error("NoSuchKey")

    content_hash = store.put(_DATA)

    fake_minio.put_object.assert_called_once()
    args = fake_minio.put_object.call_args.args
    assert args[0] == "bucket"
    assert args[1] == f"blobs/{content_hash}"


def test_minio_get_missing_blob_raises(fake_minio: MagicMock) -> None:
    store = _make_store()
    fake_minio.get_object.side_effect = _FakeS3Error("NoSuchKey")

    with pytest.raises(BlobNotFoundError):
        store.get(sha256_hex(_DATA))


def test_minio_exists_reraises_other_s3_errors(fake_minio: MagicMock) -> None:
    store = _make_store()
    fake_minio.stat_object.side_effect = _FakeS3Error("AccessDenied")

    with pytest.raises(_FakeS3Error):
        store.exists(sha256_hex(_DATA))


# ------------------------------------------------------------------ env factory


def test_factory_returns_none_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET"):
        monkeypatch.delenv(key, raising=False)
    assert get_minio_content_store() is None


@pytest.mark.usefixtures("fake_minio")
def test_factory_builds_store_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "host:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("MINIO_BUCKET", "bucket")

    store = get_minio_content_store()

    assert isinstance(store, MinioContentStore)
    assert store.bucket == "bucket"
