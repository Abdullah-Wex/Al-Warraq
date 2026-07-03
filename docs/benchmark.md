# EPUB Ecosystem Benchmark

A cross-library / cross-platform feature breakdown of the EPUB tooling space, with `epubsage` positioned against it. Focus: **every relevant capability in the ecosystem**, not only features `epubsage` has.

Legend: ✅ full · 🟡 partial / limited · ❌ none · — not applicable

---

## 1. Competitor Roster

| # | Name | Language | Category | Scope |
|---|------|----------|----------|-------|
| 1 | **epubsage** (us) | Python | Inspection lib + CLI | Read-only, structural + content extraction |
| 2 | EbookLib | Python | Full read/write lib | EPUB2/3 authoring + parsing |
| 3 | epub-meta | Python | Metadata-only lib | Zero-dep metadata + TOC reader |
| 4 | epub-toc | Python | TOC lib | Hierarchical TOC → JSON |
| 5 | epub-utils | Python | Inspection CLI + lib | Container/package/manifest/spine view |
| 6 | fast-ebook | Python (Rust core) | Full lib | Fast read/write/validate/md |
| 7 | ebookmeta | Python | Metadata read/write | epub2/3, fb2 |
| 8 | epub (crate) | Rust | Read lib | Navigation, TOC, metadata |
| 9 | epub-builder | Rust | Write lib | Generation only |
| 10 | @smoores/epub | JS/TS (Node) | Full lib | EPUB 3 inspect/modify/create |
| 11 | epub.js | JS (browser) | Renderer | Pagination, CFI, display |
| 12 | foliate-js | JS (browser) | Renderer | Rendering + search + TTS + annotations |
| 13 | @lingo-reader/epub-parser | JS/TS | Parser | Multi-format (EPUB/MOBI/AZW3/FB2), decryption |
| 14 | @gxl/epub-parser | JS/TS | Parser | EPUB → JS object |
| 15 | Readium (SDK / Mobile / Web / CSS) | C++/Swift/Kotlin/TS | Reader framework | Full reading-system stack, CFI, nav |
| 16 | Calibre (`ebook-convert`) | Python/C++ | Platform + CLI | Library mgmt + universal conversion |
| 17 | Pandoc | Haskell | Converter | N↔N format conversion incl. EPUB |
| 18 | Foliate (app) | Vala/GTK | Reader app | Linux desktop reader |
| 19 | Thorium Reader | TS/Electron | Reader app | Cross-platform Readium-based |
| 20 | Readest | Tauri/Next.js | Reader app | Cross-platform modern reader |

---

## 2. Master Feature Matrix

### 2.1 Format & Spec Support

| Library | EPUB 2 | EPUB 3 | MOBI | AZW3 | FB2 | KF8 | PDF | Other |
|---|---|---|---|---|---|---|---|---|
| epubsage | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| EbookLib | ✅ | ✅ | 🟡 (Kindle basic) | ❌ | ❌ | ❌ | ❌ | — |
| epub-meta | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| epub-toc | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| epub-utils | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| fast-ebook | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| ebookmeta | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | — |
| epub (Rust) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| @smoores/epub | 🟡 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| epub.js | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| foliate-js | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | 🟡 | CBZ, FB2 |
| @lingo-reader | ✅ | ✅ (3.3) | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| Readium | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (LCP) | Audiobooks, DiViNa |
| Calibre | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | LIT, LRF, PDB, RTF, ODT… (~25) |
| Pandoc | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (output) | 50+ formats |

### 2.2 Core Operations

| Library | Read | Write | Create from scratch | Modify in place | Validate |
|---|---|---|---|---|---|
| epubsage | ✅ | ❌ | ❌ | ❌ | 🟡 (structural) |
| EbookLib | ✅ | ✅ | ✅ | ✅ | ❌ |
| epub-meta | ✅ | ❌ | ❌ | ❌ | ❌ |
| epub-toc | ✅ | ❌ | ❌ | ❌ | ❌ |
| epub-utils | ✅ | ❌ | ❌ | ❌ | ❌ |
| fast-ebook | ✅ | ✅ | ✅ | ✅ | ✅ |
| epub (Rust) | ✅ | ❌ | ❌ | ❌ | ❌ |
| epub-builder | ❌ | ✅ | ✅ | ❌ | ❌ |
| @smoores/epub | ✅ | ✅ | ✅ | ✅ | 🟡 |
| @lingo-reader | ✅ | ❌ | ❌ | ❌ | ❌ |
| epub.js / foliate-js | ✅ (display) | ❌ | ❌ | ❌ | ❌ |
| Calibre | ✅ | ✅ | ✅ | ✅ | ✅ (`epub-fix`) |
| Pandoc | ✅ | ✅ | ✅ | ❌ | ❌ |

### 2.3 Metadata

| Library | Dublin Core | Custom OPF meta | Cover image | Identifiers (ISBN/UUID) | Series | Raw OPF access |
|---|---|---|---|---|---|---|
| epubsage | 🟡 (title only) | ❌ | ❌ | ❌ | ❌ | ✅ (opf_path) |
| EbookLib | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ |
| epub-meta | ✅ | 🟡 | ✅ (base64) | ✅ | ❌ | ✅ |
| epub-toc | ✅ | ❌ | ✅ (path) | ✅ | ✅ | ❌ |
| epub-utils | ✅ | ✅ | 🟡 | ✅ | ❌ | ✅ |
| fast-ebook | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ |
| ebookmeta | ✅ | ✅ | ✅ (r/w) | ✅ | ✅ | ✅ |
| epub (Rust) | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ |
| @smoores/epub | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ |
| @lingo-reader | ✅ | 🟡 | ✅ | ✅ | ❌ | ❌ |
| Readium | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calibre | ✅ | ✅ | ✅ | ✅ | ✅ (first-class) | ✅ |

### 2.4 Structure: Manifest / Spine / Package

| Library | Manifest iteration | Spine order | Item by ID | Item by media-type | Package-level view |
|---|---|---|---|---|---|
| epubsage | 🟡 (internal only) | ❌ | ❌ | 🟡 | ❌ |
| EbookLib | ✅ | ✅ | ✅ | ✅ | ✅ |
| epub-utils | ✅ | ✅ | ✅ | ✅ | ✅ |
| fast-ebook | ✅ | ✅ | ✅ (78× faster) | ✅ | ✅ |
| epub (Rust) | ✅ (HashMap) | ✅ | ✅ | ✅ | ✅ |
| @smoores/epub | ✅ | ✅ | ✅ | ✅ | ✅ |
| @lingo-reader | ✅ | ✅ (`getSpine`) | ✅ | ✅ | ✅ |
| epub.js / foliate-js | ✅ | ✅ | ✅ | ✅ | ✅ |
| Readium | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.5 TOC Handling

| Library | NCX parse | NAV parse | Hierarchical tree | Classification (chapter/part/FM/BM) | JSON export | Flat-TOC grouping |
|---|---|---|---|---|---|---|
| **epubsage** | ✅ | ✅ | ✅ | ✅ (3-signal heuristic) | ❌ | ✅ (chapters under parts) |
| EbookLib | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| epub-meta | 🟡 | 🟡 | ✅ (by level) | ❌ | ❌ | ❌ |
| epub-toc | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| epub-utils | ✅ | ✅ | ✅ | ❌ | 🟡 | ❌ |
| fast-ebook | ✅ | ✅ | ✅ | ❌ | 🟡 | ❌ |
| epub (Rust) | ✅ | ✅ | ✅ (`Vec<NavPoint>`) | ❌ | ❌ | ❌ |
| @smoores/epub | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| @lingo-reader | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| epub.js | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| foliate-js | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Readium | ✅ | ✅ | ✅ | ❌ | ✅ (Readium JSON) | ❌ |
| Calibre | ✅ | ✅ | ✅ | 🟡 (heading detect) | ❌ | ❌ |

### 2.6 Content Extraction & Output Formats

| Library | Raw HTML | Plaintext | Markdown | By anchor slice | Boundary detection | Exclude ranges | Preserve `<pre>` |
|---|---|---|---|---|---|---|---|
| **epubsage** | ✅ | ✅ | ✅ | ✅ | ✅ (TOC-aware) | ✅ | ✅ |
| EbookLib | ✅ | 🟡 (+BS4) | ❌ | ❌ | ❌ | ❌ | — |
| epub-meta | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| epub-toc | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| epub-utils | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | — |
| fast-ebook | ✅ | ✅ | ✅ (whole book) | ❌ | ❌ | ❌ | 🟡 |
| epub (Rust) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| @smoores/epub | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| @lingo-reader | ✅ (`loadChapter`) | 🟡 | ❌ | ❌ | ❌ | ❌ | — |
| epub.js | ✅ | ❌ | ❌ | 🟡 (CFI range) | ✅ (CFI) | ❌ | — |
| foliate-js | ✅ | ✅ | ❌ | ✅ (CFI range) | ✅ | ❌ | — |
| Readium | ✅ | ✅ | ❌ | ✅ (Locator) | ✅ | ❌ | — |
| Calibre | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | — |
| Pandoc | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |

### 2.7 Rendering / Display Features (reader-oriented)

| Library | Pagination | Fixed layout | Reflowable | CFI | Locator | Media overlays (SMIL) |
|---|---|---|---|---|---|---|
| epubsage | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| epub.js | ✅ (CSS multi-column) | ✅ | ✅ | ✅ | 🟡 | 🟡 |
| foliate-js | ✅ (bisect-accurate) | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Readium | ✅ | ✅ | ✅ | ✅ | ✅ (Readium Locator) | ✅ |
| Thorium/Readest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calibre (viewer) | ✅ | ✅ | ✅ | 🟡 | 🟡 | 🟡 |
| (parser libs) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 2.8 Reader UX Features

| Library | Full-text search | TTS | Highlights / annotations | Bookmarks | Themes / CSS | Dictionary / translate |
|---|---|---|---|---|---|---|
| epubsage | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| epub.js | 🟡 (external) | ❌ | 🟡 (plugin) | 🟡 | ✅ | ❌ |
| foliate-js | ✅ (Intl.Collator/Segmenter) | ✅ (SSML output) | ✅ (JSON-stored) | ✅ | ✅ | ✅ |
| Readium / Thorium | ✅ | ✅ | ✅ | ✅ | ✅ (Readium CSS) | 🟡 |
| Foliate / Readest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calibre | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.9 Security & Robustness

| Library | Zip-bomb guard | Zip-slip guard | Size cap | Fail-fast errors | DRM / LCP | Decryption |
|---|---|---|---|---|---|---|
| **epubsage** | ✅ (>100×) | ✅ | ✅ (2 GB) | ✅ | ❌ | ❌ |
| EbookLib | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ |
| epub-meta | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ |
| epub-utils | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ |
| fast-ebook | 🟡 (Rust safety) | 🟡 | 🟡 | ✅ | ❌ | ❌ |
| epub (Rust) | 🟡 | 🟡 | ❌ | 🟡 | ❌ | ❌ |
| @smoores/epub | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ |
| @lingo-reader | ❌ | ❌ | ❌ | 🟡 | ❌ | ✅ (RSA+AES hybrid) |
| Readium | ✅ | ✅ | ✅ | ✅ | ✅ (LCP) | ✅ |
| Calibre | ✅ | ✅ | ✅ | ✅ | 🟡 (plugins) | 🟡 |

### 2.10 Conversion & Transforms

| Library | EPUB → MD | EPUB → HTML | EPUB → PDF | EPUB → TXT | Non-EPUB → EPUB | CSS embedding | Font embed |
|---|---|---|---|---|---|---|---|
| epubsage | ✅ (per section) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| fast-ebook | ✅ (whole book) | 🟡 | ❌ | ❌ | ❌ | ❌ | ❌ |
| EbookLib | ❌ | ✅ | ❌ | 🟡 | ✅ | ✅ | ✅ |
| Calibre | ✅ | ✅ | ✅ | ✅ | ✅ (25 fmts) | ✅ | ✅ |
| Pandoc | ✅ | ✅ | ✅ | ✅ | ✅ (50+ fmts) | ✅ | ✅ |

### 2.11 Interface Surface

| Library | Python API | CLI | JS/TS API | Rust API | REST / MCP | Other bindings |
|---|---|---|---|---|---|---|
| **epubsage** | ✅ | ✅ (5 cmds, Typer+Rich) | ❌ | ❌ | ❌ | — |
| EbookLib | ✅ | ❌ | ❌ | ❌ | ❌ | — |
| epub-meta | ✅ | ❌ | ❌ | ❌ | ❌ | — |
| epub-utils | ✅ | ✅ (rich tables, XML highlight) | ❌ | ❌ | ❌ | — |
| fast-ebook | ✅ | 🟡 | ❌ | ✅ (native) | ❌ | — |
| epub (Rust) | ❌ | ❌ | ❌ | ✅ | ❌ | — |
| @smoores/epub | ❌ | ❌ | ✅ | ❌ | ❌ | Deno |
| @lingo-reader | ❌ | ❌ | ✅ | ❌ | ✅ (`epub-mcp`) | — |
| Readium | ❌ | ❌ | ✅ | ❌ | ✅ (Readium Web Services) | Swift, Kotlin, C++ |
| Calibre | ✅ | ✅ (many) | ❌ | ❌ | ✅ (content server) | — |
| Pandoc | ❌ | ✅ | ❌ | ❌ | ❌ | Haskell API |

### 2.12 Dependencies & Weight

| Library | External deps | Lines of code | Install size | Runtime |
|---|---|---|---|---|
| **epubsage** | `typer`, `markdownify` (rest stdlib) | ~1 k | small | Python 3.12+ |
| epub-meta | **zero** | ~600 | tiny | Py 2/3 |
| EbookLib | `lxml`, `six` | ~4 k | medium | Py 3 |
| epub-toc | `lxml` | ~1 k | small | Py 3 |
| epub-utils | Rich-based | ~2 k | small | Py 3 |
| fast-ebook | PyO3 + Rust core | Rust | medium | Py 3 |
| @smoores/epub | Node stdlib + xmldom | ~5 k | small | Node ≥ 18 |
| epub.js | — | ~10 k | medium | Browser |
| foliate-js | — | ~15 k | medium | Browser |
| Readium | Multi-repo | huge | large | Cross |
| Calibre | PyQt + ~30 deps | huge | ~300 MB | Desktop |

### 2.13 Performance Posture

| Library | Claim / approach |
|---|---|
| epubsage | stdlib XML + ZIP; no benchmarks published. Aimed at inspection, not hot paths. |
| fast-ebook | Rust core via PyO3. Claims **3× faster** full read/extract, **78× faster** `get_item_with_id` vs EbookLib. |
| EbookLib | `lxml`-based; fine for authoring, slow on large books. |
| epub (Rust) | native Rust speed; HashMap resource index. |
| epub.js | browser; pagination known-slow on large books. |
| foliate-js | same CSS-multicol approach but bisect location — faster than epub.js for current-range queries. |
| Readium | C++ core + native platforms — production-grade performance. |
| Calibre | pipelined conversion; optimized for batch, not per-op latency. |

### 2.14 License

| Library | License |
|---|---|
| epubsage | (project-defined) |
| EbookLib | AGPL-3.0 |
| epub-meta | MIT |
| epub-toc | MIT |
| epub-utils | MIT |
| fast-ebook | MIT |
| epub (Rust) | MIT |
| @smoores/epub | MIT |
| epub.js | BSD-2 |
| foliate-js | MIT |
| @lingo-reader | MIT |
| Readium | BSD-3 |
| Calibre | GPL-3.0 |
| Pandoc | GPL-2.0+ |

---

## 3. Where Each Tool Wins

| Tool | Strongest at |
|---|---|
| **epubsage** | TOC **semantic classification**, anchor-scoped content slicing with TOC-boundary awareness, multi-format extraction (HTML/TXT/MD) at section granularity, hardened ZIP safety. |
| EbookLib | De-facto Python authoring, plugin system, TOC/NCX/NAV generation. |
| epub-meta | Zero-dep metadata snapshot in 5 lines. |
| epub-toc | TOC → structured JSON pipeline. |
| epub-utils | Prettiest terminal inspection UX (Rich tables, XML highlight). |
| fast-ebook | Raw speed + whole-book markdown. |
| ebookmeta | Metadata **round-trip** (read + write) incl. FB2. |
| epub (Rust) | Embeddable reader core for Rust apps. |
| @smoores/epub | Modern Node EPUB 3 authoring. |
| @lingo-reader | Multi-format + **DRM decryption**. |
| epub.js / foliate-js / Readium | Actual in-browser rendering, CFI, paging, TTS, annotations. |
| Calibre | Universal library manager + 25-format conversion. |
| Pandoc | Format-matrix conversion hub. |

## 4. Where `epubsage` is Unique

1. **TOC classification** with chapter/part/front-matter/back-matter/section/subsection/minor tags — **nothing else in this roster does this**.
2. **Anchor-scoped content extraction with boundary detection** — slices exactly one TOC entry out of a file, respecting sibling TOC anchors, supporting child anchors as non-boundaries and excludes. epub.js/foliate-js/Readium have CFI ranges but require explicit start/end; `epubsage` infers them from TOC structure.
3. **Triple output format per section** (HTML / plaintext / Markdown) at the same granularity.
4. **Fail-fast ZIP hardening** (bomb + slip + 2 GB cap) baked into a parser lib — rare outside Readium/Calibre.

## 5. Where `epubsage` Is Behind

- No write / authoring path (EbookLib, fast-ebook, @smoores/epub, epub-builder).
- No full metadata API beyond title (every other lib).
- No manifest / spine iteration API (all others).
- No benchmarks published (fast-ebook sets the bar).
- No JSON export of TOC (epub-toc, Readium JSON).
- No rendering, CFI, search, TTS, annotations (readers).
- No DRM / LCP (Readium, @lingo-reader).
- No non-EPUB format support (Calibre, Pandoc, @lingo-reader, foliate-js).

---

## 6. Sources

- [EbookLib — GitHub](https://github.com/aerkalov/ebooklib) · [docs](https://docs.sourcefabric.org/projects/ebooklib/en/latest/)
- [epub-meta](https://github.com/paulocheque/epub-meta)
- [epub-toc — PyPI](https://pypi.org/project/epub-toc/)
- [epub-utils — GitHub](https://github.com/ernestofgonzalez/epub-utils) · [docs](https://ernestofgonzalez.github.io/epub-utils/)
- [fast-ebook](https://github.com/arc53/fast-ebook)
- [ebookmeta](https://github.com/dnkorpushov/ebookmeta)
- [epub crate — docs.rs](https://docs.rs/epub/latest/epub/) · [epub-builder](https://docs.rs/epub-builder)
- [@smoores/epub — npm](https://www.npmjs.com/package/@smoores/epub) · [announcement](https://smoores.dev/post/announcing_smoores_epub/)
- [@lingo-reader/epub-parser](https://www.npmjs.com/package/@lingo-reader/epub-parser) · [lingo-reader repo](https://github.com/hhk-png/lingo-reader)
- [@gxl/epub-parser](https://github.com/gaoxiaoliangz/epub-parser)
- [epub.js](https://github.com/futurepress/epub.js/)
- [foliate-js](https://github.com/johnfactotum/foliate-js) · [architecture](https://deepwiki.com/johnfactotum/foliate-js/2-core-components)
- [Readium SDK overview](https://readium.org/development/readium-sdk-overview/) · [Navigator architecture](https://readium.org/technical/r2-navigator-architecture/) · [CFI](https://readium.org/readium-sdk/api/html/class_c_f_i.xhtml)
- [Calibre `ebook-convert`](https://manual.calibre-ebook.com/generated/en/ebook-convert.html) · [manual](https://manual.calibre-ebook.com/)
- [Pandoc EPUB](https://pandoc.org/epub.html)
- [Foliate](https://johnfactotum.github.io/foliate/) · [Readest](https://github.com/readest/readest) · [Thorium](https://www.edrlab.org/software/thorium-reader/)
