"""BM25 full-text search over an EPUB, backed by a persisted SQLite index.

Pure-Python BM25 (no third-party deps). The index is an inverted index stored in
SQLite at ``<output_dir>/<hash>/bm25_index.db``, keyed by the EPUB's file hash so
repeat searches reuse it. Each searchable "document" is a single TOC
section/sub-section (its own text, children excluded), so hits pinpoint exactly
where a term occurs; results carry a ``book > chapter > section`` breadcrumb plus
``file``/``anchor`` for chaining into ``extract_content``.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .content import extract_content
from .epub import extract_epub, hash_epub
from .exceptions import InvalidEpubError
from .ncx import NavPoint
from .storage import resolve_output_dir
from .toc import anchors_by_file, classified_roots, descendant_anchors

# BM25 free parameters (Robertson/Lucene defaults).
K1 = 1.5
B = 0.75

# Keep tech tokens intact: ``next.js``, ``_app.js``, ``ci/cd`` -> ``ci`` ``cd``.
_TOKEN_RE = re.compile(r"[a-z0-9_][a-z0-9._-]*")

_DB_NAME = "bm25_index.db"

# Tags whose appearance in a breadcrumb marks a chapter-rollup boundary.
_CHAPTER_TAGS = ("chapter", "part", "front_matter", "back_matter")

# Map the public format name to extract_content's output_format argument.
_FMT: dict[str, str | None] = {"html": None, "plaintext": "plaintext", "markdown": "markdown"}


@dataclass
class SearchHit:
    """A single BM25 search result."""

    score: float
    breadcrumb: list[str]
    tags: list[str]
    file: str
    anchor: str | None
    n_sections: int = 1
    content: str | None = None


@dataclass
class _Chunk:
    breadcrumb: list[str]
    tags: list[str]
    file: str
    anchor: str | None
    tokens: list[str] = field(default_factory=list)
    n_chars: int = 0


def tokenize(text: str) -> list[str]:
    """Lowercase and split into search tokens, preserving tech identifiers."""
    return _TOKEN_RE.findall(text.lower())


# --------------------------------------------------------------------------- #
# Chunk collection (reuses TOC parse/classify + extract_all_sections)         #
# --------------------------------------------------------------------------- #
def _collect_chunks(epub_path: str, output_dir: str | None) -> tuple[list[_Chunk], str]:
    """Extract per-section plaintext for every TOC node with its breadcrumb.

    Each node is extracted with its file's anchor set for boundary detection and
    its own descendants excluded, so a section's text never includes its
    children's. Per-node extraction (rather than ``extract_all_sections``)
    tolerates publisher quirks where a sibling anchor lives in another file.
    """
    extract_dir = extract_epub(epub_path, output_dir or resolve_output_dir())
    roots, title, opf_dir = classified_roots(extract_dir)
    file_anchors = anchors_by_file(roots)

    chunks: list[_Chunk] = []

    def walk(points: list[NavPoint], trail_labels: list[str], trail_tags: list[str]) -> None:
        for pt in points:
            labels = [*trail_labels, pt.label]
            tags = [*trail_tags, pt.nav_type or "section"]
            text = ""
            html_path = opf_dir / pt.file if pt.file else None
            if html_path and html_path.exists():
                try:
                    text = extract_content(
                        str(html_path), pt.anchor,
                        file_anchors.get(pt.file, []),
                        child_anchors=descendant_anchors(pt.children),
                        output_format="plaintext",
                    )
                except InvalidEpubError:
                    text = ""
            chunks.append(_Chunk(
                breadcrumb=labels,
                tags=tags,
                file=pt.file,
                anchor=pt.anchor,
                tokens=tokenize(text),
                n_chars=len(text),
            ))
            walk(pt.children, labels, tags)

    walk(roots, [], [])
    return chunks, title


# --------------------------------------------------------------------------- #
# SQLite inverted index                                                       #
# --------------------------------------------------------------------------- #
def _db_path(epub_path: str, output_dir: str | None) -> Path:
    base = Path(output_dir or resolve_output_dir())
    return base / hash_epub(epub_path) / _DB_NAME


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            breadcrumb TEXT, tags TEXT, file TEXT, anchor TEXT,
            len INTEGER, n_chars INTEGER
        );
        CREATE TABLE terms (term TEXT PRIMARY KEY, df INTEGER, idf REAL);
        CREATE TABLE postings (term TEXT, chunk_id INTEGER, tf INTEGER);
        CREATE INDEX idx_post_term ON postings(term);
        """
    )


def build_search_index(
    epub_path: str, output_dir: str | None = None, *, force: bool = False,
) -> Path:
    """Build (or reuse) the SQLite BM25 index for ``epub_path``.

    Returns the database path. Skips rebuilding when a db already exists for
    this EPUB's hash unless ``force`` is set.
    """
    db_path = _db_path(epub_path, output_dir)
    if db_path.exists() and not force:
        return db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    chunks, title = _collect_chunks(epub_path, output_dir)
    n = len(chunks)
    avgdl = (sum(len(c.tokens) for c in chunks) / n) if n else 0.0

    df: Counter[str] = Counter()
    for c in chunks:
        df.update(set(c.tokens))

    conn = sqlite3.connect(db_path)
    try:
        _create_schema(conn)
        conn.executemany(
            "INSERT INTO meta(key, value) VALUES (?, ?)",
            [("book_title", title), ("N", str(n)),
             ("avgdl", repr(avgdl)), ("k1", repr(K1)), ("b", repr(B))],
        )
        conn.executemany(
            "INSERT INTO terms(term, df, idf) VALUES (?, ?, ?)",
            [(t, d, math.log(1 + (n - d + 0.5) / (d + 0.5))) for t, d in df.items()],
        )
        for chunk_id, c in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks(id, breadcrumb, tags, file, anchor, len, n_chars) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chunk_id, json.dumps(c.breadcrumb), json.dumps(c.tags),
                 c.file, c.anchor, len(c.tokens), c.n_chars),
            )
            tf = Counter(c.tokens)
            conn.executemany(
                "INSERT INTO postings(term, chunk_id, tf) VALUES (?, ?, ?)",
                [(term, chunk_id, count) for term, count in tf.items()],
            )
        conn.commit()
    finally:
        conn.close()
    return db_path


# --------------------------------------------------------------------------- #
# Query                                                                       #
# --------------------------------------------------------------------------- #
def _score(conn: sqlite3.Connection, q_terms: list[str]) -> list[SearchHit]:
    avgdl = float(conn.execute(
        "SELECT value FROM meta WHERE key='avgdl'").fetchone()[0])
    avgdl = avgdl or 1.0

    # Accumulate BM25 per chunk, touching only postings for the query terms.
    scores: dict[int, float] = {}
    placeholders = ",".join("?" * len(q_terms))
    rows = conn.execute(
        f"SELECT p.chunk_id, p.tf, t.idf, c.len "  # noqa: S608  # nosec B608
        f"FROM postings p "
        f"JOIN terms t ON t.term = p.term "
        f"JOIN chunks c ON c.id = p.chunk_id "
        f"WHERE p.term IN ({placeholders})",
        q_terms,
    ).fetchall()
    for chunk_id, tf, idf, dl in rows:
        dl = dl or 1
        denom = tf + K1 * (1 - B + B * dl / avgdl)
        scores[chunk_id] = scores.get(chunk_id, 0.0) + idf * (tf * (K1 + 1)) / denom

    if not scores:
        return []

    ids = ",".join(str(i) for i in scores)
    meta = {
        row[0]: row
        for row in conn.execute(
            f"SELECT id, breadcrumb, tags, file, anchor FROM chunks "  # noqa: S608  # nosec B608
            f"WHERE id IN ({ids})",
        ).fetchall()
    }
    hits = [
        SearchHit(
            score=score,
            breadcrumb=json.loads(meta[cid][1]),
            tags=json.loads(meta[cid][2]),
            file=meta[cid][3],
            anchor=meta[cid][4],
        )
        for cid, score in scores.items()
    ]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits


def _rollup_chapter(hits: list[SearchHit]) -> list[SearchHit]:
    """Collapse hits to their nearest chapter/part ancestor (max-of-children)."""
    groups: dict[tuple[str, ...], SearchHit] = {}
    for h in hits:
        key_idx = 0
        for i, tag in enumerate(h.tags):
            if tag in _CHAPTER_TAGS:
                key_idx = i
        crumb = h.breadcrumb[: key_idx + 1]
        key = tuple(crumb)
        existing = groups.get(key)
        if existing is None:
            groups[key] = SearchHit(
                score=h.score, breadcrumb=crumb, tags=h.tags[: key_idx + 1],
                file=h.file, anchor=h.anchor, n_sections=1,
            )
        else:
            existing.n_sections += 1
            if h.score > existing.score:
                existing.score = h.score
                existing.file = h.file
                existing.anchor = h.anchor
    out = list(groups.values())
    out.sort(key=lambda h: h.score, reverse=True)
    return out


def _attach_content(
    epub_path: str,
    hits: list[SearchHit],
    content_format: str,
    output_dir: str | None,
) -> None:
    """Fill ``hit.content`` for each hit by re-extracting its section body.

    Parses the TOC once and reuses the same boundary helpers as indexing so a
    section's content excludes its children's. Only called for the limited hit
    set, so the extra parse is cheap.
    """
    out_fmt = _FMT[content_format]
    extract_dir = extract_epub(epub_path, output_dir or resolve_output_dir())
    roots, _, opf_dir = classified_roots(extract_dir)
    file_anchors = anchors_by_file(roots)

    node_by_key: dict[tuple[str, str], NavPoint] = {}

    def index_nodes(points: list[NavPoint]) -> None:
        for pt in points:
            if pt.file:
                node_by_key[(pt.file, pt.anchor or "")] = pt
            index_nodes(pt.children)

    index_nodes(roots)

    for hit in hits:
        node = node_by_key.get((hit.file, hit.anchor or ""))
        html_path = opf_dir / hit.file if hit.file else None
        if html_path is None or not html_path.exists():
            hit.content = ""
            continue
        try:
            hit.content = extract_content(
                str(html_path), hit.anchor,
                file_anchors.get(hit.file, []),
                child_anchors=descendant_anchors(node.children) if node else [],
                output_format=out_fmt,
            )
        except InvalidEpubError:
            hit.content = ""


def search(
    epub_path: str,
    query: str,
    *,
    group: str = "section",
    limit: int = 10,
    output_dir: str | None = None,
    with_content: bool = False,
    content_format: str = "html",
) -> list[SearchHit]:
    """Search ``epub_path`` for ``query`` and return ranked hits.

    ``group``: ``"section"`` (leaf hits), ``"chapter"`` (max-of-children rollup),
    or ``"flat"`` (top-N ignoring hierarchy — same shape as ``"section"``).

    When ``with_content`` is set, each returned hit's ``content`` is populated
    with its section body in ``content_format`` (``"html"``, ``"plaintext"`` or
    ``"markdown"``).
    """
    q_terms = tokenize(query)
    if not q_terms:
        return []
    db_path = build_search_index(epub_path, output_dir)
    conn = sqlite3.connect(db_path)
    try:
        hits = _score(conn, q_terms)
    finally:
        conn.close()
    if group == "chapter":
        hits = _rollup_chapter(hits)
    hits = hits[:limit]
    if with_content:
        _attach_content(epub_path, hits, content_format, output_dir)
    return hits
