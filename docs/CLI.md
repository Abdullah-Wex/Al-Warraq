# Al-Warraq CLI Reference

Command-line interface documentation for Al-Warraq v1.0.0.

## Overview

Al-Warraq provides 6 commands for EPUB inspection from the terminal.

```bash
al-warraq --help
```

![CLI Help](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-help.png?raw=true)

---

## Global Options

| Option | Description |
|--------|-------------|
| `--version`, `-V` | Show version and exit |
| `--help` | Show help message |

---

## Output contract

Every command follows the same contract:

| Rule | Behavior |
|------|----------|
| `--json` | Available on every command — prints a single JSON object to stdout, unstyled |
| Streams | Results go to **stdout**; errors, warnings, and notices go to **stderr** |
| Exit codes | `0` success · `1` operational failure (e.g. invalid EPUB — `validate` exits 1) · `2` usage error |
| Errors | One red line + a `--help` hint — never a full help dump |
| `content` | Prints pure data to stdout, so `al-warraq content … > chapter.md` just works |
| Color | Auto-disabled when piped; honors `NO_COLOR` |

```bash
al-warraq inspect book.epub --json | jq .version
al-warraq search book.epub "transformers" --json | jq '.results[0].anchor'
al-warraq validate book.epub --json && echo "valid"
```

## Commands

### inspect

Display basic EPUB information: version, TOC type, title.

```bash
al-warraq inspect <PATH> [--output-dir DIR]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir`, `-o` | System temp | Extraction directory |

```bash
al-warraq inspect book.epub
```

![CLI Inspect](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-inspect.png?raw=true)

---

### extract

Extract EPUB contents to a directory (unzip).

```bash
al-warraq extract <PATH> [--output-dir DIR]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir`, `-o` | System temp | Extraction directory |

```bash
al-warraq extract book.epub -o ./extracted
```

---

### validate

Validate an EPUB file: checks ZIP structure, OPF presence, and TOC.

```bash
al-warraq validate <PATH>
```

```bash
al-warraq validate book.epub
```

![CLI Validate](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-validate.png?raw=true)

---

### toc

Display table of contents as a classified tree.

```bash
al-warraq toc <PATH> [--output-dir DIR]
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
al-warraq toc book.epub
```

![CLI TOC](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-toc.png?raw=true)

---

### content

Extract content for a specific TOC section by anchor ID, file path, or both.

```bash
al-warraq content <PATH> [OPTIONS]
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
al-warraq content book.epub --anchor "ch01_intro"
```

![CLI Content HTML](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-content-html.png?raw=true)

**Plaintext output:**

```bash
al-warraq content book.epub --anchor "ch01_intro" --parse-to plaintext
```

![CLI Content Plaintext](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-content-plaintext.png?raw=true)

**Markdown output:**

```bash
al-warraq content book.epub --anchor "ch01_intro" --parse-to markdown
```

![CLI Content Markdown](https://github.com/Abdullah-Wex/Al-Warraq/blob/main/docs/screenshots/cli-content-markdown.png?raw=true)

**File + anchor:**

```bash
al-warraq content book.epub --file "ch01.html" --anchor "section_2"
```

**Exclude sections:**

```bash
al-warraq content book.epub --anchor "ch01_intro" --exclude "footnotes,bibliography"
```

---

## Environment

| Variable | Description |
|----------|-------------|
| `AL_WARRAQ_DEBUG` | Set to `1` or `true` for full exception tracebacks |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operational failure (invalid EPUB, not found, no TOC) |
| 2 | Usage error (missing/invalid arguments) |

## See Also

- [API Reference](API.md)
- [Examples](EXAMPLES.md)
