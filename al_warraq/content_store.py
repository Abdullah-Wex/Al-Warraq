"""ContentStore — content-addressed, deduplicated blob storage for EPUBs.

Identical bytes are stored exactly once: ``put()`` hashes the data first and
skips the write when the blob already exists, always returning the same
``content_hash`` (full SHA-256 hex) for the same bytes.

The store is mechanism only. Reference counting, ownership, and access
control belong to the host application — ``delete()`` removes a blob
unconditionally and the store never decides who may read what.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .exceptions import BlobNotFoundError

if TYPE_CHECKING:
    from minio import Minio  # type: ignore[import-not-found]

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

_MINIO_ENV = (
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MINIO_BUCKET",
)


def sha256_hex(data: bytes) -> str:
    """Full SHA-256 hex digest — the ContentStore's content_hash."""
    return hashlib.sha256(data).hexdigest()


def is_content_hash(value: str) -> bool:
    """True iff ``value`` is a well-formed content_hash (64 lowercase hex)."""
    return bool(_HASH_RE.match(value))


@runtime_checkable
class ContentStore(Protocol):
    """Content-addressed blob storage: hash in, bytes out."""

    def put(self, data: bytes) -> str:
        """Store ``data`` once; return its content_hash (no-op if it exists)."""
        ...

    def exists(self, content_hash: str) -> bool:
        """True iff a blob with this hash is stored."""
        ...

    def get(self, content_hash: str) -> bytes:
        """Return the blob's bytes; raise BlobNotFoundError when missing."""
        ...

    def delete(self, content_hash: str) -> None:
        """Remove the blob unconditionally. Reference counting is the host's job."""
        ...


class LocalContentStore:
    """Filesystem-backed ContentStore: one file per blob at ``root/<hash>``."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes) -> str:
        content_hash = sha256_hex(data)
        blob = self._blob_path(content_hash)
        if blob.exists():
            return content_hash
        tmp = blob.with_name(f"tmp-{content_hash}")
        tmp.write_bytes(data)
        os.replace(tmp, blob)  # atomic: readers never see a partial blob
        return content_hash

    def exists(self, content_hash: str) -> bool:
        return self._blob_path(content_hash).exists()

    def get(self, content_hash: str) -> bytes:
        blob = self._blob_path(content_hash)
        if not blob.exists():
            raise BlobNotFoundError(f"No blob stored for hash {content_hash}")
        return blob.read_bytes()

    def delete(self, content_hash: str) -> None:
        self._blob_path(content_hash).unlink(missing_ok=True)

    def _blob_path(self, content_hash: str) -> Path:
        return self.root / content_hash


class MinioContentStore:
    """MinIO-backed ContentStore: one object per blob at ``<prefix><hash>``.

    Shares a bucket safely with the extraction cache (``MinioCache``) because
    blobs live under their own prefix. Requires the ``minio`` extra.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        prefix: str = "blobs/",
    ) -> None:
        from minio import Minio  # type: ignore[import-not-found]

        self.bucket = bucket
        self.prefix = prefix
        self.client: Minio = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def put(self, data: bytes) -> str:
        import io

        content_hash = sha256_hex(data)
        if self.exists(content_hash):
            return content_hash
        self.client.put_object(
            self.bucket, self._object_name(content_hash),
            io.BytesIO(data), length=len(data),
        )
        return content_hash

    def exists(self, content_hash: str) -> bool:
        from minio.error import S3Error  # type: ignore[import-not-found]

        try:
            self.client.stat_object(self.bucket, self._object_name(content_hash))
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
        return True

    def get(self, content_hash: str) -> bytes:
        from minio.error import S3Error  # type: ignore[import-not-found]

        try:
            response = self.client.get_object(
                self.bucket, self._object_name(content_hash),
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise BlobNotFoundError(
                    f"No blob stored for hash {content_hash}"
                ) from e
            raise
        try:
            return bytes(response.read())
        finally:
            response.close()
            response.release_conn()

    def delete(self, content_hash: str) -> None:
        self.client.remove_object(self.bucket, self._object_name(content_hash))

    def _object_name(self, content_hash: str) -> str:
        return f"{self.prefix}{content_hash}"


def get_minio_content_store() -> MinioContentStore | None:
    """Build ``MinioContentStore`` from env vars, or ``None`` if unconfigured."""
    if not all(os.environ.get(k) for k in _MINIO_ENV):
        return None
    secure = os.environ.get("MINIO_SECURE", "").lower() in ("1", "true", "yes")
    try:
        return MinioContentStore(
            endpoint=os.environ["MINIO_ENDPOINT"],
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            bucket=os.environ["MINIO_BUCKET"],
            secure=secure,
        )
    except ImportError:
        return None
