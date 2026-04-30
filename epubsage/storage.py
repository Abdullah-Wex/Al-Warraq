"""Output-dir resolution and optional MinIO-backed extraction cache."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from minio import Minio  # type: ignore[import-not-found]

_ENV_OUTPUT_DIR = "EPUBSAGE_OUTPUT_DIR"
_MINIO_ENV = (
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MINIO_BUCKET",
)


def resolve_output_dir() -> str:
    """Return ``EPUBSAGE_OUTPUT_DIR`` if set, else ``<tempdir>/epubsage``."""
    return os.environ.get(_ENV_OUTPUT_DIR) or str(
        Path(tempfile.gettempdir()) / "epubsage"
    )


class MinioCache:
    """Thin MinIO wrapper scoped to a single bucket, keyed by file hash."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        from minio import Minio  # type: ignore[import-not-found]

        self.bucket = bucket
        self.client: Minio = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def has(self, file_hash: str) -> bool:
        """True iff any object with prefix ``<file_hash>/`` exists."""
        prefix = f"{file_hash}/"
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=False)
        for _ in objects:
            return True
        return False

    def download(self, file_hash: str, local_dir: Path) -> None:
        """Pull every object under ``<file_hash>/`` into ``local_dir/<file_hash>/``."""
        prefix = f"{file_hash}/"
        for obj in self.client.list_objects(
            self.bucket, prefix=prefix, recursive=True,
        ):
            if obj.object_name is None:
                continue
            rel = obj.object_name[len(prefix):]
            target = local_dir / file_hash / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            self.client.fget_object(
                self.bucket, obj.object_name, str(target),
            )

    def upload(self, file_hash: str, local_dir: Path) -> None:
        """Push every file under ``local_dir/<file_hash>/`` to ``<file_hash>/`` prefix."""
        root = local_dir / file_hash
        if not root.is_dir():
            return
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            self.client.fput_object(
                self.bucket, f"{file_hash}/{rel}", str(path),
            )


def get_minio_cache() -> MinioCache | None:
    """Build ``MinioCache`` from env vars, or ``None`` if unconfigured."""
    if not all(os.environ.get(k) for k in _MINIO_ENV):
        return None
    secure = os.environ.get("MINIO_SECURE", "").lower() in ("1", "true", "yes")
    try:
        return MinioCache(
            endpoint=os.environ["MINIO_ENDPOINT"],
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            bucket=os.environ["MINIO_BUCKET"],
            secure=secure,
        )
    except ImportError:
        return None
