# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Interactive terminal app: `al-warraq book.epub` (path only) opens a
  Textual browser — header, scrollable results pane, bottom input with
  `/` slash commands (`/toc /search /content /info /open /help /quit`);
  bare text runs BM25 search. Installed via the `tui` extra; without a
  TTY or without the extra, path-only invocation falls back to `inspect`.
- `Book.section_by_ref()` — resolve a single reference as a TOC anchor
  first, then as a chapter file.
- Reusable renderable builders in `output.py` (`build_kv`,
  `build_toc_tree`, `build_search_results`, `inspect_pairs`) shared by
  the CLI and the interactive app.

## [1.0.0] - 2026-07-03

### Changed
- **Project renamed: epubsage → Al-Warraq (الورّاق).** Install `al-warraq`, import `al_warraq`, CLI `al-warraq`.
- Exception base class renamed: `EpubSageError` → `AlWarraqError`.
- Environment variables renamed: `EPUBSAGE_*` → `AL_WARRAQ_*`.
- Default output directory: `<tempdir>/al-warraq`.
- The `epubsage` package on PyPI is deprecated at 0.7.1 and will receive no further updates.

## [0.5.0] - 2026-03-25

### Added

- `parse_ncx()` and `parse_nav()` — NCX (EPUB 2) and NAV (EPUB 3) TOC parsing with fallback for non-standard formats
- `classify_navpoint()` and `classify_children()` — NavPoint classification (chapter, part, front/back matter, section, subsection, minor)
- `extract_content()` — content extraction with HTML, plaintext, and markdown output
- `NavPoint` and `NcxData` dataclasses for structured TOC data
- `toc` CLI command — display TOC as a classified tree with type tags
- `content` CLI command — extract section content (`--anchor`, `--file`, `--exclude`, `--parse-to`)
- Zip bomb detection (compression ratio > 100x) and zip slip prevention
- `AL_WARRAQ_DEBUG` environment variable for full exception tracebacks

### Changed

- Complete API rewrite: replaced class-based architecture with 10 functions and 4 dataclasses
- CLI rewritten from 15 commands to 5 (`inspect`, `extract`, `validate`, `toc`, `content`)
- Dependencies: replaced `beautifulsoup4`, `lxml`, `pydantic` with `markdownify`
- Package structure: flat module layout (9 files in `al_warraq/`) replaces nested subdirectories
- TOC path resolution now handles non-root OPF directories and non-standard NCX filenames
- Documentation fully rewritten

### Removed

- All old classes: `SimpleEpubProcessor`, `DublinCoreParser`, `EpubStructureParser`, `ContentClassifier`, `SearchService`, `EpubExtractor`
- All old modules: `core/`, `extractors/`, `processors/`, `services/`, `utils/`
- Old CLI commands: `info`, `stats`, `chapters`, `metadata`, `images`, `search`, `classify`, `spine`, `manifest`, `chapter`, `list`, `cover`
- `storage/` module and related exceptions
- `example_usage.py`
- Old test suite (to be rewritten for new API)

## [0.3.0] - 2025-01-09

### Added

- **TOC-Based Content Extraction** - Extract content using Table of Contents anchor boundaries for precise section splitting
  - `NavigationPoint.anchor` and `NavigationPoint.file_path` fields for parsed href components
  - New `toc_content_extractor.py` module with:
    - `SectionBoundary` model for defining content boundaries
    - `ExtractedSection` model for extracted section content
    - `build_section_boundaries()` function to compute section boundaries per file
    - `extract_book_by_toc()` function for full book extraction
  - `EpubStructureParser.extract_content_by_toc()` method for TOC-based extraction
- Precise section splitting based on publisher-defined TOC structure instead of header-based detection
- **Chapter Sections** - Each chapter now includes a `sections` field with TOC-based hierarchical content
  - Section structure: `id`, `title`, `level`, `content`, `images`, `word_count`, `subsections`
  - Nested `subsections` array matches TOC tree structure exactly
  - Uses existing TOC extraction for precise section boundaries

### Changed

- **CLI Rewrite** - Complete rewrite using Typer and Rich for better UX
  - New `al_warraq/cli/` directory structure
  - Commands: info, content, export, images, media, metadata
  - Modern CLI with colors and rich output
- **Code Modularization** - Split monolithic files into focused modules
  - Extractors: element_extractors, specialized_extractors, html_parser, image_resolver
  - Processors: orchestrator, content_consolidator, helpers, result
  - Major code reduction (-4,405 lines, +639 lines)
- Converted dataclasses to Pydantic models for consistency

### Fixed

- Type annotation fixes for mypy strict mode compliance
- Proper Optional types for model fields

## [0.2.0] - 2025-01-03

### Added

- CLI commands with basic output
- Comprehensive documentation

## [0.1.1] - 2024-12-30

### Fixed

- Build configuration improvements

## [0.1.0] - 2024-12-30

### Added

- Initial release of Al-Warraq
- **Core Parsers**
  - `DublinCoreParser` - Full Dublin Core metadata extraction (15 elements)
  - `EpubStructureParser` - Complete EPUB structure analysis
  - `TocParser` - Table of Contents parsing (NCX and nav documents)
  - `ContentClassifier` - Pattern-based content classification
- **Extractors**
  - `EpubExtractor` - ZIP extraction and file management
  - `content_extractor` - HTML content extraction with header detection
- **Processors**
  - `SimpleEpubProcessor` - One-step EPUB processing pipeline
  - `SimpleEpubResult` - Flat result dataclass
- **Services**
  - `SearchService` - Full-text search across chapters
  - `save_to_json` - JSON export with datetime support
- **Models**
  - Pydantic models for Dublin Core metadata
  - Pydantic models for EPUB structure
- **CLI**
  - `al-warraq extract` - Extract EPUB to JSON
  - `epubsage info` - Display metadata
  - `epubsage list` - List chapters
- **Utilities**
  - XML namespace handling
  - Text statistics and reading time estimation
- Publisher-agnostic pattern recognition (Manning, O'Reilly, Packt, etc.)
- Type hints throughout with `py.typed` marker
- Comprehensive test suite (60+ tests)

[Unreleased]: https://github.com/Abdullah-Wex/Al-Warraq/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Abdullah-Wex/Al-Warraq/compare/v0.3.0...v0.5.0
[0.3.0]: https://github.com/Abdullah-Wex/Al-Warraq/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Abdullah-Wex/Al-Warraq/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/Abdullah-Wex/Al-Warraq/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Abdullah-Wex/Al-Warraq/releases/tag/v0.1.0
