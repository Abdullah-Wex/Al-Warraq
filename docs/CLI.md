# EpubSage CLI Reference

Command-line interface documentation for EpubSage v0.5.0.

## Overview

EpubSage provides 5 commands for EPUB inspection from the terminal.

```bash
epubsage --help
```

![CLI Help](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-help.png?raw=true)

---

## Global Options

| Option | Description |
|--------|-------------|
| `--version`, `-V` | Show version and exit |
| `--help` | Show help message |

---

## Commands

### inspect

Display basic EPUB information: version, TOC type, title.

```bash
epubsage inspect <PATH> [--output-dir DIR]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir`, `-o` | System temp | Extraction directory |

```bash
epubsage inspect book.epub
```

![CLI Inspect](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-inspect.png?raw=true)

---

### extract

Extract EPUB contents to a directory (unzip).

```bash
epubsage extract <PATH> [--output-dir DIR]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir`, `-o` | System temp | Extraction directory |

```bash
epubsage extract book.epub -o ./extracted
```

---

### validate

Validate an EPUB file: checks ZIP structure, OPF presence, and TOC.

```bash
epubsage validate <PATH>
```

```bash
epubsage validate book.epub
```

![CLI Validate](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-validate.png?raw=true)

---

### toc

Display table of contents as a classified tree.

```bash
epubsage toc <PATH> [--output-dir DIR]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir`, `-o` | System temp | Extraction directory |

Each entry shows a type tag and the section's anchor or file reference:

| Tag | Type | Color |
|-----|------|-------|
| `CH` | Chapter | Green |
| `PT` | Part | Cyan |
| `FM` | Front matter | Dim |
| `BM` | Back matter | Dim |
| `S1` | Section | Blue |
| `S2` | Subsection | Dim blue |
| `S3` | Minor | Dim |

```bash
epubsage toc book.epub
```

![CLI TOC](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-toc.png?raw=true)

---

### content

Extract content for a specific TOC section by anchor ID, file path, or both.

```bash
epubsage content <PATH> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--anchor`, `-a` | TOC anchor ID |
| `--file`, `-f` | Chapter file path (relative to EPUB) |
| `--exclude`, `-x` | Comma-separated anchor IDs to exclude |
| `--parse-to`, `-p` | Output format: `plaintext`, `markdown` (default: raw HTML) |
| `--output-dir`, `-o` | Extraction directory |

At least one of `--anchor` or `--file` is required. Both can be used together.

**HTML output (default):**

```bash
epubsage content book.epub --anchor "ch01_intro"
```

![CLI Content HTML](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-content-html.png?raw=true)

**Plaintext output:**

```bash
epubsage content book.epub --anchor "ch01_intro" --parse-to plaintext
```

![CLI Content Plaintext](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-content-plaintext.png?raw=true)

**Markdown output:**

```bash
epubsage content book.epub --anchor "ch01_intro" --parse-to markdown
```

![CLI Content Markdown](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/cli-content-markdown.png?raw=true)

**File + anchor:**

```bash
epubsage content book.epub --file "ch01.html" --anchor "section_2"
```

**Exclude sections:**

```bash
epubsage content book.epub --anchor "ch01_intro" --exclude "footnotes,bibliography"
```

---

## Environment

| Variable | Description |
|----------|-------------|
| `EPUBSAGE_DEBUG` | Set to `1` or `true` for full exception tracebacks |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid EPUB, missing argument, anchor not found) |

---

## See Also

- [API Reference](API.md)
- [Examples](EXAMPLES.md)
