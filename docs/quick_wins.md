# al-warraq — Quick Wins

> Competitive gap analysis from [`benchmark.md`](./benchmark.md), turned into a prioritized feature roadmap.
> **"Quick win"** = high impact, low cost, reusing parsers we already have.

---

## Table of Contents

- [Current Baseline](#current-baseline)
- [Summary Matrix](#summary-matrix)
- [Tier 1 — Tiny Effort, Outsized Value](#tier-1--tiny-effort-outsized-value)
- [Tier 2 — Medium Effort, Strong Differentiation](#tier-2--medium-effort-strong-differentiation)
- [Tier 3 — Bigger Bets](#tier-3--bigger-bets)
- [Recommended Sprint Order](#recommended-sprint-order)

---

## Current Baseline

What `al-warraq` ships today (v0.5.0):

| Area | Status |
|---|---|
| EPUB 2 / 3 read | ✅ |
| OPF discovery + version | ✅ |
| Title (DC) | ✅ |
| NCX + NAV parsing | ✅ |
| TOC classification (chapter/part/FM/BM/section) | ✅ |
| Anchor-scoped content extraction | ✅ |
| Output formats (HTML / plaintext / Markdown) | ✅ |
| ZIP hardening (bomb + slip + 2 GB cap) | ✅ |
| CLI (Typer + Rich) — 5 commands | ✅ |

---

## Summary Matrix

| Tier | Feature | Effort | Lines | Closes gap vs. |
|---|---|---|---|---|
| **1.1** | Full Dublin Core metadata | ~2 h | ~20 | epub-meta, epub-utils, EbookLib |
| **1.2** | Cover image resolution | ~1 h | ~15 | epub-meta, fast-ebook, EbookLib |
| **1.3** | Manifest + Spine access | ~3 h | ~30 | epub-utils, EbookLib, Readium |
| **1.4** | TOC → JSON export | ~1 h | ~10 | epub-toc, Readium |
| **1.5** | Find by id / href | ~1 h | ~10 | fast-ebook (78×) |
| **1.6** | `--format {rich,json,plain}` CLI | ~3 h | ~40 | epub-utils |
| **1.7** | Resource bytes by id/href | ~1 h | ~15 | all reader libs |
| **2.1** | Whole-book markdown export | ~2 d | ~50 | fast-ebook, Pandoc |
| **2.2** | Real validation + report | ~3 d | ~100 | Calibre `epub-fix` |
| **2.3** | Full-text search | ~3 d | ~80 | foliate-js, Calibre *(no Python peer)* |
| **2.4** | Published benchmarks | ~1 d | — | fast-ebook |
| **2.5** | NCX `pageList` + landmarks | ~1 d | ~40 | Readium, Calibre |
| **2.6** | Reading-order iterator | ~1 d | ~30 | all reader libs |
| **3.1** | Full resource manifest | ~1 wk | — | readers |
| **3.2** | Heading-based TOC fallback | ~1 wk | — | Calibre *(unique in Python)* |
| **3.3** | CFI mint + resolve | ~2 wk | — | Readium, epub.js, foliate-js |
| **3.4** | MOBI / AZW3 / FB2 read | ~1 mo | — | foliate-js, @lingo-reader |
| **3.5** | Write / authoring path | ~1 mo | — | EbookLib, fast-ebook *(skip unless needed)* |

---

## Tier 1 — Tiny Effort, Outsized Value

> **Theme:** we already parse the tree — we just don't expose it. Most of Tier 1 is a single PR.

---

### 1.1 Full Dublin Core Metadata

| | |
|---|---|
| **Gap** | We parse `<dc:title>` only. Every competitor exposes author, language, identifier, publisher, date, description, subject, rights. |
| **Fix** | Extend `EpubInfo` with a `Metadata` dataclass; one loop over `{DC_NS}*` children in `opf.py`. |
| **Impact** | Matches baseline of epub-meta / epub-utils / EbookLib. Without this we can't be recommended as a metadata tool. |

---

### 1.2 Cover Image Resolution

| | |
|---|---|
| **Gap** | No cover lookup. epub-meta, epub-toc, fast-ebook, EbookLib all do it. |
| **Fix** | Scan manifest for `properties="cover-image"` (EPUB 3) and `<meta name="cover">` → id lookup (EPUB 2). Add `cover_path: Path \| None` to `EpubInfo`. |
| **Impact** | Unlocks thumbnails for any host app (including Sage Reader). |

---

### 1.3 Manifest + Spine Access

| | |
|---|---|
| **Gap** | Manifest is parsed internally but nothing is exposed. epub-utils/EbookLib/fast-ebook/Readium all expose iterators. |
| **Fix** | `ManifestItem(id, href, media_type, properties)` dataclass + `list_manifest(info)` / `list_spine(info)` helpers. |
| **Impact** | Turns `al-warraq` from "TOC inspector" into "package inspector." Essential for any resource-iterating consumer. |

---

### 1.4 TOC → JSON Export

| | |
|---|---|
| **Gap** | epub-toc's entire selling point. Readium has Readium JSON. |
| **Fix** | `NavPoint` is already a dataclass → one `asdict` call + CLI flag `--json` on the `toc` command. |
| **Impact** | Drop-in replacement for epub-toc users; machine-readable output for pipelines. |

---

### 1.5 Find by `id` / by `href`

| | |
|---|---|
| **Gap** | fast-ebook brags about **78× faster** `get_item_with_id`. We don't even have the method. |
| **Fix** | Build `items_by_id` / `items_by_href` dicts once during `parse_opf`. O(1) lookup. |
| **Impact** | Matches every reader library; simplifies our own `content` command internally. |

---

### 1.6 `--format {rich,json,plain}` on Every CLI Command

| | |
|---|---|
| **Gap** | epub-utils ships multi-format output (XML, JSON, plaintext, table). We only do Rich tables. |
| **Fix** | Global `--format` option via a Typer callback that routes command results. |
| **Impact** | CLI becomes scriptable — required for pipelines, CI, and editor integrations. |

---

### 1.7 Resource Extraction by `id` / `href`

| | |
|---|---|
| **Gap** | "Give me the bytes of this image/CSS/font." Every other lib does this. |
| **Fix** | `get_resource(info, id_or_href) -> bytes` reading from the extract directory. |
| **Impact** | Enables cover/image/CSS workflows without re-parsing. |

---

## Tier 2 — Medium Effort, Strong Differentiation

> **Theme:** features that require new code but give us parity — or in some cases, leadership — in the Python EPUB space.

---

### 2.1 Whole-Book Markdown / Plaintext Export

| | |
|---|---|
| **Gap** | fast-ebook's headline feature ("War and Peace → one markdown"). Pandoc and Calibre do it too. |
| **Fix** | Iterate spine → call existing `extract_content(..., anchor=None)` per file → concatenate. New command: `al-warraq export --format md book.epub`. |
| **Impact** | Instant parity with fast-ebook using code we already have. HTML→MD and `<pre>` preservation already solved. |

---

### 2.2 Validation With a Real Report

| | |
|---|---|
| **Gap** | Our `validate` only checks "parses." Calibre has `epub-fix`; Readium has full validation. |
| **Fix** | Check: OPF well-formed, every manifest href exists, every spine idref resolves, NCX/NAV present, cover present, no orphan files. Return a structured report. |
| **Impact** | A pre-flight check nobody in the Python lib space does cleanly. |

---

### 2.3 Full-Text Search Across the Book

| | |
|---|---|
| **Gap** | foliate-js, Readium, Calibre, Foliate all have it. **No Python lib does.** |
| **Fix** | Walk spine → plaintext (already have) → word/regex search with context snippets + locator `(file, anchor)`. CLI: `al-warraq search book.epub "quantum"`. |
| **Impact** | **New capability with no Python competitor** — a rare positional gap. |

---

### 2.4 Published Benchmarks

| | |
|---|---|
| **Gap** | fast-ebook publishes numbers; we don't. Invisible performance reads as "assumed slow." |
| **Fix** | `benchmarks/` with `pytest-benchmark` against 10–20 real EPUBs. Compare us vs. EbookLib vs. fast-ebook on parse / TOC / content / export. |
| **Impact** | Legitimizes the project. Even losing to fast-ebook is fine — showing the number matters. Likely wins vs. EbookLib on inspection. |

---

### 2.5 NCX `pageList` + Landmarks

| | |
|---|---|
| **Gap** | Readium and Calibre use these for a11y + navigation. We ignore them. |
| **Fix** | Parse `<pageList>` in NCX and `<nav epub:type="landmarks">` in NAV alongside main TOC. |
| **Impact** | Accessibility story; mapping to print page numbers for citation use-cases. |

---

### 2.6 Reading-Order Iteration

| | |
|---|---|
| **Gap** | Every reader library exposes `spine → chapter → content`. We force users through the TOC. |
| **Fix** | `iter_reading_order(info) -> Iterator[Chapter]` walking spine, yielding `(idref, href, html_path, toc_entry?)`. |
| **Impact** | Linear-reading apps (most of them) don't have to write this glue themselves. Pairs with 2.1 and 3.3. |

---

## Tier 3 — Bigger Bets

> **Theme:** weeks of work. Only pursue if Sage Reader or external users need them.

---

### 3.1 Full Resource Manifest
Extract all images/fonts/CSS with sizes + mime types. Useful for any viewer UI.

### 3.2 Heading-Based TOC Fallback
When `toc_type="unknown"`, scan spine HTML for `<h1>`/`<h2>` and synthesize a TOC. Calibre does this. **Unique in the Python lib space.**

### 3.3 CFI (Content Fragment Identifier) — Mint & Resolve
EPUB 3 standard locator. Readium, epub.js, foliate-js have it. Without CFI we can't interop with reader apps. Pairs well with 2.6.

### 3.4 MOBI / AZW3 / FB2 Reading
Matches foliate-js and @lingo-reader. Only worth it if Sage Reader needs non-EPUB formats.

### 3.5 Authoring / Write Path
Huge scope, duplicates EbookLib + fast-ebook. **Skip** unless a concrete host-app need emerges.

---

## Recommended Sprint Order

```text
Sprint 1 (1 PR)   → Tier 1.1–1.7 bundled: metadata + cover + manifest/spine
                                         + JSON + lookups + resource bytes
Sprint 2          → T2.1 (whole-book export) — fast-ebook parity
Sprint 3          → T2.4 (benchmarks)        — makes everything defensible
Sprint 4          → T2.3 (search)            — first "no-Python-peer" feature
Backlog           → T2.2 / T2.5 / T2.6 as bandwidth allows
Later             → Tier 3 on demand only
```

**Key insight:** all of Tier 1 reuses trees we already parse. There is **no new parser code** — only exposure. One PR doubles our public API surface for under a day of work.
