"""process_epub — from stored bytes to passage- and embedding-ready output.

The pipeline: fetch the blob from a ContentStore → extract → parse metadata
and TOC → assemble chapters in reading order → split each chapter into
passages (PassageSplitter) → optionally embed them (Embedder).

Output is deterministic: identical bytes processed with the same strategies
produce identical output, so hosts can share one index per unique book.
``ProcessedBook.schema_version`` bumps whenever the output shape changes.

The pipeline holds no policy: it makes no access decisions and never calls
back into the host — the two injected strategies are the only host code run.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .content import extract_content
from .content_store import ContentStore, is_content_hash, sha256_hex
from .epub import extract_epub, find_opf
from .exceptions import InvalidEpubError
from .hooks import Embedder, PassageSplitter, StructuralSplitter
from .ncx import NavPoint
from .opf import parse_opf
from .storage import resolve_output_dir
from .toc import anchors_by_file, classified_roots, descendant_anchors

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BookMetadata:
    """Descriptive metadata of a processed book."""

    title: str | None
    creator: str | None
    publisher: str | None
    epub_version: str
    toc_type: str


@dataclass(frozen=True)
class ProcessedChapter:
    """One chapter-level unit of the book, in reading order."""

    index: int
    title: str
    nav_type: str
    file: str
    anchor: str | None
    text: str


@dataclass(frozen=True)
class Passage:
    """One retrievable passage with its stable location metadata."""

    passage_id: str
    content_hash: str
    chapter_index: int
    position: int
    text: str
    char_start: int | None
    char_end: int | None
    vector: list[float] | None = None


@dataclass(frozen=True)
class ProcessedBook:
    """Everything ``process_epub`` produces, under one schema version."""

    schema_version: int
    content_hash: str
    metadata: BookMetadata
    chapters: list[ProcessedChapter] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Stable plain-dict form for serialization and comparison."""
        return asdict(self)


def process_epub(
    content_hash: str,
    store: ContentStore,
    *,
    splitter: PassageSplitter | None = None,
    embedder: Embedder | None = None,
    output_dir: str | None = None,
) -> ProcessedBook:
    """Process a stored EPUB into metadata, chapters, and passages.

    ``splitter`` defaults to :class:`StructuralSplitter`; without an
    ``embedder`` no vectors are computed. ``output_dir`` is the extraction
    cache directory (defaults to the standard one).
    """
    if not is_content_hash(content_hash):
        raise ValueError(
            f"content_hash must be 64 lowercase hex chars, got: {content_hash!r}"
        )
    splitter = splitter or StructuralSplitter()
    out = output_dir or resolve_output_dir()

    extract_dir = _ensure_extracted(content_hash, store, out)
    metadata = _read_metadata(extract_dir)
    chapters = _assemble_chapters(extract_dir)
    passages = _split_into_passages(content_hash, chapters, splitter)
    if embedder is not None:
        passages = _embed(passages, embedder)

    return ProcessedBook(
        schema_version=SCHEMA_VERSION,
        content_hash=content_hash,
        metadata=metadata,
        chapters=chapters,
        passages=passages,
    )


# ------------------------------------------------------------------ pipeline


def _ensure_extracted(content_hash: str, store: ContentStore, out: str) -> Path:
    """Extract the stored blob, reusing the shared extraction cache.

    Extraction directories are keyed by the 16-char hash prefix — the same
    key ``extract_epub`` derives from the bytes, so path-based and
    store-based processing share one cache entry per unique book.
    """
    extract_dir = Path(out) / content_hash[:16]
    if extract_dir.exists() and any(extract_dir.iterdir()):
        return extract_dir

    data = store.get(content_hash)  # raises BlobNotFoundError when missing
    if sha256_hex(data) != content_hash:
        raise InvalidEpubError(
            f"Stored blob does not match its content hash: {content_hash}"
        )

    Path(out).mkdir(parents=True, exist_ok=True)
    epub_file = Path(out) / f"{content_hash[:16]}.epub"
    epub_file.write_bytes(data)
    try:
        return extract_epub(str(epub_file), out)
    finally:
        epub_file.unlink(missing_ok=True)


def _read_metadata(extract_dir: Path) -> BookMetadata:
    """Dublin Core + structural metadata from the OPF."""
    opf_path = find_opf(str(extract_dir))
    info = parse_opf(str(opf_path), str(extract_dir))
    return BookMetadata(
        title=info.title,
        creator=info.creator,
        publisher=info.publisher,
        epub_version=info.version,
        toc_type=info.toc.toc_type,
    )


def _assemble_chapters(extract_dir: Path) -> list[ProcessedChapter]:
    """Chapter-level units from the classified TOC, in reading order.

    A part contributes its own introductory text and then recurses, so its
    chapters become units of their own; any other unit's text includes all
    of its descendants. A book without a TOC yields no chapters.
    """
    roots, _, opf_dir = classified_roots(extract_dir)
    file_anchors = anchors_by_file(roots)
    chapters: list[ProcessedChapter] = []

    def add(pt: NavPoint, text: str) -> None:
        chapters.append(ProcessedChapter(
            index=len(chapters),
            title=pt.label,
            nav_type=pt.nav_type or "section",
            file=pt.file,
            anchor=pt.anchor,
            text=text,
        ))

    def walk(points: list[NavPoint]) -> None:
        for pt in points:
            if pt.nav_type == "part":
                add(pt, _own_text(pt, opf_dir, file_anchors))
                walk(pt.children)
            else:
                add(pt, _unit_text(pt, opf_dir, file_anchors))

    walk(roots)
    return chapters


def _unit_text(
    pt: NavPoint, opf_dir: Path, file_anchors: dict[str, list[str]],
) -> str:
    """A node's text plus all of its descendants', in reading order."""
    parts = [_own_text(pt, opf_dir, file_anchors)]
    for child in pt.children:
        parts.append(_unit_text(child, opf_dir, file_anchors))
    return "\n\n".join(p for p in parts if p)


def _own_text(
    pt: NavPoint, opf_dir: Path, file_anchors: dict[str, list[str]],
) -> str:
    """One TOC node's own plaintext, bounded so children are excluded."""
    if not pt.file:
        return ""
    html_path = opf_dir / pt.file
    if not html_path.exists():
        return ""
    try:
        return extract_content(
            str(html_path), pt.anchor,
            file_anchors.get(pt.file, []),
            child_anchors=descendant_anchors(pt.children),
            output_format="plaintext",
        ).strip()
    except InvalidEpubError:
        return ""


def _split_into_passages(
    content_hash: str,
    chapters: list[ProcessedChapter],
    splitter: PassageSplitter,
) -> list[Passage]:
    """Run the splitter per chapter; assign stable positions and offsets.

    ``char_start``/``char_end`` locate the passage inside its chapter's text;
    they are None when the splitter transformed the text beyond recognition.
    """
    passages: list[Passage] = []
    for chapter in chapters:
        if not chapter.text:
            continue
        cursor = 0
        for position, text in enumerate(splitter.split(chapter.text)):
            start = chapter.text.find(text, cursor)
            if start >= 0:
                end: int | None = start + len(text)
                cursor = start + 1
            else:
                start, end = -1, None
            passages.append(Passage(
                passage_id=(
                    f"{content_hash[:16]}"
                    f"-c{chapter.index:03d}-p{position:04d}"
                ),
                content_hash=content_hash,
                chapter_index=chapter.index,
                position=position,
                text=text,
                char_start=start if start >= 0 else None,
                char_end=end,
            ))
    return passages


def _embed(passages: list[Passage], embedder: Embedder) -> list[Passage]:
    """One batched embed call over the whole book; attach the vectors."""
    vectors = embedder.embed([p.text for p in passages])
    if len(vectors) != len(passages):
        raise ValueError(
            f"Embedder returned {len(vectors)} vectors for {len(passages)} passages"
        )
    return [
        Passage(
            passage_id=p.passage_id,
            content_hash=p.content_hash,
            chapter_index=p.chapter_index,
            position=p.position,
            text=p.text,
            char_start=p.char_start,
            char_end=p.char_end,
            vector=[float(v) for v in vector],
        )
        for p, vector in zip(passages, vectors, strict=True)
    ]
