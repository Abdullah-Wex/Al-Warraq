"""EPUB file handling — hash, extract, find OPF."""

import hashlib
import os
import zipfile
from pathlib import Path

from .exceptions import InvalidEpubError
from .storage import get_minio_cache


def is_epub_package(path: Path) -> bool:
    """True iff ``path`` is a directory laid out as an unzipped EPUB.

    Some reading apps (and this library's own extraction) store books as
    expanded folders rather than zip files: ``mimetype`` + ``META-INF/`` +
    an OPF somewhere inside.
    """
    return path.is_dir() and (
        (path / "META-INF" / "container.xml").is_file()
        or (path / "mimetype").is_file()
    )


def hash_epub(epub_path: str) -> str:
    """Content hash of an EPUB (first 16 hex chars of SHA-256).

    Works for both zipped ``.epub`` files and unzipped EPUB package
    directories; for directories the hash covers every file's relative
    path and bytes in sorted order, so it is deterministic and moves with
    the content, not the location.
    """
    path = Path(epub_path)
    sha256 = hashlib.sha256()

    if is_epub_package(path):
        for file in sorted(p for p in path.rglob("*") if p.is_file()):
            sha256.update(str(file.relative_to(path)).encode())
            sha256.update(file.read_bytes())
        return sha256.hexdigest()[:16]

    if not path.is_file():
        raise InvalidEpubError(f"EPUB file not found: {epub_path}")
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


def extract_epub(epub_path: str, output_dir: str) -> Path:
    """Extract EPUB to output_dir/<hash>/. Returns extraction directory.

    An unzipped EPUB package directory is already "extracted": it is
    returned as-is and parsed in place — no copy, no zip guards needed.
    """
    path = Path(epub_path)
    if is_epub_package(path):
        return path
    if not path.is_file():
        raise InvalidEpubError(f"EPUB file not found: {epub_path}")

    file_hash = hash_epub(epub_path)
    extract_dir = Path(output_dir) / file_hash

    # Local cache — reuse an existing non-empty extraction.
    if extract_dir.exists() and any(extract_dir.iterdir()):
        return extract_dir

    # MinIO cache — download when remote copy exists.
    cache = get_minio_cache()
    if cache is not None and cache.has(file_hash):
        extract_dir.mkdir(parents=True, exist_ok=True)
        cache.download(file_hash, Path(output_dir))
        return extract_dir

    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(path, "r") as zf:
            # Zip bomb check
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            compressed_size = os.path.getsize(epub_path)
            ratio = total_uncompressed / compressed_size if compressed_size > 0 else 0
            if ratio > 100:
                raise InvalidEpubError(
                    f"Zip bomb detected: compression ratio {ratio:.0f}x exceeds limit"
                )
            size_mb = total_uncompressed / (1024 * 1024)
            if total_uncompressed > 2 * 1024 * 1024 * 1024:
                raise InvalidEpubError(
                    f"EPUB too large: {size_mb:.0f}MB exceeds 2GB limit"
                )

            # Zip slip check
            real_extract_dir = os.path.realpath(extract_dir)
            for member in zf.namelist():
                target = os.path.realpath(os.path.join(extract_dir, member))
                if not target.startswith(real_extract_dir + os.sep) and target != real_extract_dir:
                    raise InvalidEpubError(
                        f"Zip slip attack detected: {member} escapes extraction directory"
                    )

            zf.extractall(extract_dir)
    except zipfile.BadZipFile as e:
        raise InvalidEpubError(f"Not a valid ZIP/EPUB file: {epub_path}") from e

    if cache is not None:
        cache.upload(file_hash, Path(output_dir))

    return extract_dir


def find_opf(epub_dir: str) -> Path:
    """Find the .opf file in an extracted EPUB directory."""
    base = Path(epub_dir)

    # Check common paths first
    for candidate in [
        base / "content.opf",
        base / "OEBPS" / "content.opf",
        base / "OPS" / "content.opf",
    ]:
        if candidate.exists():
            return candidate

    # Fallback: search recursively
    for opf_file in base.rglob("*.opf"):
        return opf_file

    raise InvalidEpubError(f"No .opf file found in {epub_dir} — not a valid EPUB")
