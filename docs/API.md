# Al-Warraq API Reference

Complete Python API documentation for Al-Warraq v0.5.0.

## Quick Start

```python
from al_warraq import inspect_epub

info = inspect_epub("book.epub")
print(f"Title:   {info.title}")
print(f"Version: EPUB {info.version}")
print(f"TOC:     {info.toc.toc_type}")
```

![Quick Start](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/python-quickstart.png?raw=true)

---

## Functions

### inspect_epub

One-step inspection: hash, extract, parse OPF, detect TOC.

```python
from al_warraq import inspect_epub, EpubInfo

info: EpubInfo = inspect_epub(epub_path: str, output_dir: str | None = None)  # None → user cache dir
```

**Parameters:**
- `epub_path` (str): Path to EPUB file.
- `output_dir` (str): Extraction directory. Defaults to system temp.

**Returns:** `EpubInfo` dataclass.

**Raises:** `InvalidEpubError` on invalid/corrupt EPUB.

---

### hash_epub

SHA-256 hash of the EPUB file (first 16 hex chars).

```python
from al_warraq import hash_epub

file_hash: str = hash_epub(epub_path: str)
```

---

### extract_epub

Extract EPUB ZIP to `output_dir/<hash>/`.

```python
from al_warraq import extract_epub
from pathlib import Path

extract_dir: Path = extract_epub(epub_path: str, output_dir: str)
```

**Security checks:** Zip bomb detection (ratio > 100x), file size limit (2GB), zip slip prevention.

---

### find_opf

Find the `.opf` file in an extracted EPUB directory.

```python
from al_warraq import find_opf
from pathlib import Path

opf_path: Path = find_opf(epub_dir: str)
```

Checks common paths (`content.opf`, `OEBPS/content.opf`, `OPS/content.opf`) then falls back to recursive search.

---

### parse_opf

Parse OPF file for version and TOC type.

```python
from al_warraq import parse_opf, EpubInfo

info: EpubInfo = parse_opf(opf_path: str, epub_dir: str | None = None)
```

---

### parse_ncx

Parse an NCX file for document title and navigation map.

```python
from al_warraq import parse_ncx, NcxData

ncx: NcxData = parse_ncx(ncx_path: str)
print(ncx.doc_title)
for pt in ncx.nav_points:
    print(f"{pt.label} -> {pt.file}#{pt.anchor}")
```

---

### parse_nav

Parse EPUB 3 NAV XHTML for TOC entries.

```python
from al_warraq import parse_nav, NavPoint

nav_points: list[NavPoint] = parse_nav(nav_path: str)
```

Returns the same `NavPoint` type as `parse_ncx`.

---

### classify_navpoint

Classify a single NavPoint by its label.

```python
from al_warraq import classify_navpoint

nav_type: str = classify_navpoint(nav_point)
# Returns: "chapter" | "part" | "front_matter" | "back_matter" | "section"
```

---

### classify_children

Classify children of already-classified NavPoints by nesting depth. Mutates `nav_type` in place.

```python
from al_warraq import classify_children

classify_children(points: list[NavPoint])
# Depth 1 children -> "section"
# Depth 2 children -> "subsection"
# Depth 3+ children -> "minor"
```

---

### extract_content

Extract HTML content for a TOC entry by anchor reference.

```python
from al_warraq import extract_content

content: str = extract_content(
    html_path: str,
    anchor: str | None,
    toc_anchors: list[str],
    child_anchors: list[str] | None = None,
    exclude: list[str] | None = None,
    output_format: str | None = None,
)
```

**Parameters:**
- `html_path` (str): Absolute path to the chapter HTML file.
- `anchor` (str | None): Element ID to start from, or `None` for entire file.
- `toc_anchors` (list[str]): All TOC anchor IDs in this file (for boundary detection).
- `child_anchors` (list[str] | None): Anchors that are children of the target in the TOC tree. These are NOT treated as stop boundaries.
- `exclude` (list[str] | None): Anchor IDs whose sections should be excluded.
- `output_format` (str | None): `"plaintext"`, `"markdown"`, or `None` for raw HTML.

**Returns:** Content string in the requested format.

**Raises:** `InvalidEpubError` if HTML cannot be parsed or anchor is not found.

---

## Storage & Processing

### ContentStore

Content-addressed, deduplicated blob storage. Identical bytes are stored
exactly once; `put()` hashes first and skips the write when the blob
already exists. The `content_hash` is the full SHA-256 hex digest.

`ContentStore` is a structural protocol — any object with these four
methods works:

```python
from al_warraq import ContentStore, LocalContentStore, MinioContentStore

store: ContentStore = LocalContentStore("/var/blobs")

content_hash = store.put(Path("book.epub").read_bytes())
store.exists(content_hash)     # True
data = store.get(content_hash) # raises BlobNotFoundError when missing
store.delete(content_hash)     # unconditional — see the boundary note
```

| Backend | Storage | Notes |
|---------|---------|-------|
| `LocalContentStore(root)` | One file per blob at `root/<hash>` | Atomic writes; good for dev/CI |
| `MinioContentStore(endpoint, access_key, secret_key, bucket, secure=False, prefix="blobs/")` | One object per blob at `<prefix><hash>` | Requires the `minio` extra; shares a bucket safely with the extraction cache |

`get_minio_content_store()` builds a `MinioContentStore` from the
`MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` / `MINIO_BUCKET`
environment variables, or returns `None` when unconfigured.

**Boundary:** the store is mechanism only. Reference counting, ownership,
and access control belong to the host application — `delete()` removes a
blob unconditionally, and the library never decides who may read what.

---

### process_epub

```python
from al_warraq import LocalContentStore, process_epub

store = LocalContentStore("/var/blobs")
content_hash = store.put(Path("book.epub").read_bytes())

result = process_epub(content_hash, store)
result.metadata.title          # "Book Title"
result.chapters[0].text        # chapter plaintext, subsections included
result.passages[0].passage_id  # "1a2b3c4d5e6f7a8b-c000-p0000"
```

**Signature:** `process_epub(content_hash, store, *, splitter=None, embedder=None, output_dir=None) -> ProcessedBook`

Pipeline: fetch the blob → verify its hash → extract (shared cache, all
zip-bomb/zip-slip guards apply) → parse metadata and TOC → assemble
chapters in reading order → split each chapter into passages → optionally
embed them.

**Deterministic:** identical bytes processed with the same strategies
produce identical output — no timestamps, no random ids — so hosts can
share one index per unique book. `ProcessedBook.schema_version`
(`SCHEMA_VERSION`, currently `1`) bumps whenever the output shape changes;
hosts should check it before consuming.

**Raises:** `ValueError` for a malformed hash, `BlobNotFoundError` when the
store has no such blob, `InvalidEpubError` for tampered or invalid content.

---

### Hooks: PassageSplitter and Embedder

The two injection points for host strategies. Both are structural
protocols; implement the method and pass the object in — the library never
calls back into the host beyond these.

```python
class SentenceSplitter:
    def split(self, chapter_text: str) -> list[str]:
        return [s for s in chapter_text.split(". ") if s]

result = process_epub(content_hash, store, splitter=SentenceSplitter())
```

| Hook | Method | Default |
|------|--------|---------|
| `PassageSplitter` | `split(chapter_text) -> Sequence[str]` | `StructuralSplitter(max_chars=2000)` — packs whole paragraphs up to the size budget |
| `Embedder` | `embed(passages) -> Sequence[Sequence[float]]` | None — no vectors computed |

The splitter returns plain strings in reading order; the pipeline assigns
positions and character offsets. The embedder gets one batched call with
every passage text of the book and must return one vector per passage.

---

## Data Types

### EpubInfo

EPUB inspection result.

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | EPUB version (`"2.0"`, `"3.0"`, etc.) |
| `toc` | `TocInfo` | TOC detection result |
| `opf_path` | `Path` | Absolute path to the OPF file |
| `title` | `str \| None` | Book title, or `None` if not found |

---

### TocInfo

TOC detection result.

| Field | Type | Description |
|-------|------|-------------|
| `toc_type` | `str` | `"nav"`, `"ncx"`, or `"unknown"` |
| `toc_href` | `str \| None` | Relative path from OPF dir |
| `toc_path` | `Path \| None` | Absolute resolved path |
| `ncx_href` | `str \| None` | NCX href (always populated if NCX exists) |
| `ncx_path` | `Path \| None` | NCX absolute path |

---

### NavPoint

A single navigation point from the TOC.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique ID |
| `label` | `str` | Display label |
| `src` | `str` | Full source reference (e.g., `ch01.html#anchor`) |
| `file` | `str` | File path without anchor |
| `anchor` | `str \| None` | Anchor ID from href |
| `children` | `list[NavPoint]` | Nested child points |
| `play_order` | `int \| None` | Reading order (NCX only) |
| `class_name` | `str \| None` | CSS class from NCX |
| `nav_type` | `str \| None` | Classification after `classify_navpoint()` |

---

### NcxData

Parsed NCX file data.

| Field | Type | Description |
|-------|------|-------------|
| `doc_title` | `str \| None` | Document title from NCX |
| `nav_points` | `list[NavPoint]` | Top-level navigation points |

---

### ProcessedBook

Everything `process_epub()` produces. `to_dict()` returns a stable plain
dict for serialization and comparison.

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `int` | Output-contract version (`SCHEMA_VERSION`) |
| `content_hash` | `str` | Full SHA-256 of the source bytes |
| `metadata` | `BookMetadata` | title, creator, publisher, epub_version, toc_type |
| `chapters` | `list[ProcessedChapter]` | index, title, nav_type, file, anchor, text |
| `passages` | `list[Passage]` | see below |

### Passage

| Field | Type | Description |
|-------|------|-------------|
| `passage_id` | `str` | Deterministic: `<hash16>-c<chapter>-p<position>` |
| `content_hash` | `str` | The book's content hash |
| `chapter_index` | `int` | Which chapter this passage belongs to |
| `position` | `int` | 0-based position within the chapter |
| `text` | `str` | The passage text |
| `char_start` / `char_end` | `int \| None` | Offsets into the chapter's text; `None` if the splitter transformed the text |
| `vector` | `list[float] \| None` | Embedding, when an `Embedder` was injected |

---

## Exceptions

```python
from al_warraq import AlWarraqError, InvalidEpubError
```

| Exception | Description |
|-----------|-------------|
| `AlWarraqError` | Base exception for all Al-Warraq errors |
| `InvalidEpubError` | EPUB file is invalid or corrupt |
| `BlobNotFoundError` | No blob with the requested content hash in the ContentStore |

---

## Error Handling

All functions raise `InvalidEpubError` immediately on:

- File not found
- Not a valid ZIP
- Zip bomb detected (compression ratio > 100x)
- File too large (> 2GB uncompressed)
- Zip slip attack detected
- No `.opf` file found
- OPF cannot parse as XML
- Missing `version` attribute in OPF

These are **not errors** (valid states):

- `toc_type = "unknown"` — no TOC found
- `title = None` — no title in metadata

```python
from al_warraq import inspect_epub, InvalidEpubError

try:
    info = inspect_epub("book.epub")
except InvalidEpubError as e:
    print(f"Invalid EPUB: {e}")
```

---

## See Also

- [CLI Reference](CLI.md)
- [Examples](EXAMPLES.md)
