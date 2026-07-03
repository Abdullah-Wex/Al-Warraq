# EpubSage

> ⚠️ **This package has been renamed to [al-warraq](https://pypi.org/project/al-warraq/).**
> `epubsage` will receive no further updates. Migrate with:
> `pip install al-warraq` and `import al_warraq`.

[![PyPI version](https://img.shields.io/pypi/v/epubsage.svg)](https://pypi.org/project/epubsage/)
[![Python versions](https://img.shields.io/pypi/pyversions/epubsage.svg)](https://pypi.org/project/epubsage/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Lightweight EPUB inspection library — version detection, TOC discovery, and content extraction.

## Features

| Feature | Description |
|---------|-------------|
| **Version Detection** | EPUB 2.0 and 3.0 support |
| **TOC Discovery** | Automatic NAV (EPUB 3) and NCX (EPUB 2) detection |
| **TOC Parsing** | Parse navigation points with full tree structure |
| **Classification** | Classify entries as chapter, part, front/back matter, section |
| **Content Extraction** | Extract content as HTML, plaintext, or markdown |
| **Security** | Zip bomb detection and zip slip prevention |
| **CLI** | 5 commands for EPUB inspection from the terminal |

## Requirements

- Python 3.10+
- Dependencies: `markdownify`, `typer`

## Installation

```bash
pip install epubsage
```

Or with `uv`:

```bash
uv add epubsage
```

## Quick Start

### Python

```python
from epubsage import inspect_epub

info = inspect_epub("book.epub")

print(f"Title:   {info.title}")
print(f"Version: EPUB {info.version}")
print(f"TOC:     {info.toc.toc_type}")
```

![Quick Start](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/python-quickstart.png?raw=true)

### Command Line

```bash
epubsage inspect book.epub
```

![CLI Inspect](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-inspect.png?raw=true)

## CLI Commands

```bash
epubsage --help
```

![CLI Help](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-help.png?raw=true)

| Command | Description |
|---------|-------------|
| `inspect` | Display EPUB version, TOC type, and title |
| `extract` | Extract EPUB contents to a directory |
| `validate` | Validate ZIP structure, OPF, and TOC |
| `toc` | Display table of contents as a classified tree |
| `content` | Extract content for a specific section |

**[Full CLI documentation →](docs/CLI.md)**

### Shell Auto-Completion

```bash
epubsage --install-completion
```

Supported shells: **Bash**, **Zsh**, **Fish**, **PowerShell**

## Python API

### Core Functions

| Function | Description |
|----------|-------------|
| `inspect_epub()` | One-step inspection: hash, extract, parse OPF, detect TOC |
| `hash_epub()` | SHA-256 hash of EPUB file |
| `extract_epub()` | Extract EPUB ZIP to directory |
| `find_opf()` | Find the `.opf` file in extracted EPUB |
| `parse_opf()` | Parse OPF for version and TOC info |
| `parse_ncx()` | Parse NCX file for navigation map |
| `parse_nav()` | Parse EPUB 3 NAV document |
| `classify_navpoint()` | Classify a NavPoint by label |
| `classify_children()` | Classify children by nesting depth |
| `extract_content()` | Extract content as HTML, plaintext, or markdown |

### Data Types

| Type | Description |
|------|-------------|
| `EpubInfo` | Inspection result: version, TOC, OPF path, title |
| `TocInfo` | TOC detection: type, paths |
| `NavPoint` | Navigation point: label, file, anchor, children, type |
| `NcxData` | Parsed NCX: doc title, nav points |

**[Full API documentation →](docs/API.md)**

**[Examples →](docs/EXAMPLES.md)**

## Architecture

```
epubsage/
├── __init__.py     # Public API: inspect_epub + re-exports
├── classify.py     # classify_navpoint, classify_children
├── cli.py          # CLI: inspect, extract, validate, toc, content
├── content.py      # extract_content (HTML, plaintext, markdown)
├── epub.py         # hash_epub, extract_epub, find_opf
├── exceptions.py   # EpubSageError, InvalidEpubError
├── nav.py          # parse_nav (EPUB 3 NAV)
├── ncx.py          # parse_ncx, NavPoint, NcxData
└── opf.py          # parse_opf, EpubInfo, TocInfo
```

## Development

```bash
git clone https://github.com/Abdullah-Wex/epubsage.git
cd epubsage
uv sync
```

```bash
make lint        # ruff
make typecheck   # mypy
make security    # bandit
make test        # pytest
make quality     # all checks
```

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/API.md) | Complete Python API documentation |
| [CLI Reference](docs/CLI.md) | All CLI commands and options |
| [Examples](docs/EXAMPLES.md) | Practical usage examples |
| [Changelog](CHANGELOG.md) | Version history |

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
