# EpubSage Examples

Practical examples for EpubSage v0.5.0.

---

## Inspect a Book

```python
from epubsage import inspect_epub

info = inspect_epub("book.epub")

print(f"Title:   {info.title}")
print(f"Version: EPUB {info.version}")
print(f"TOC:     {info.toc.toc_type}")
print(f"OPF:     {info.opf_path}")
```

![Quick Start](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/python-quickstart.png?raw=true)

---

## Parse TOC and Classify

```python
from epubsage import inspect_epub, parse_ncx, classify_navpoint, classify_children

info = inspect_epub("book.epub")
ncx = parse_ncx(str(info.toc.ncx_path))

# Classify top-level entries
for pt in ncx.nav_points:
    pt.nav_type = classify_navpoint(pt)

# Classify children by depth
classify_children(ncx.nav_points)

for pt in ncx.nav_points[:5]:
    print(f"[{pt.nav_type}] {pt.label}")
    for child in pt.children[:3]:
        print(f"  [{child.nav_type}] {child.label}")
```

![TOC Classification](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/python-toc.png?raw=true)

For EPUB 3 files with NAV instead of NCX:

```python
from epubsage import inspect_epub, parse_nav, classify_navpoint, classify_children

info = inspect_epub("book.epub")
nav_points = parse_nav(str(info.toc.toc_path))

for pt in nav_points:
    pt.nav_type = classify_navpoint(pt)
classify_children(nav_points)
```

---

## Extract Content

### HTML (default)

```python
from epubsage import inspect_epub, parse_ncx, extract_content

info = inspect_epub("book.epub")
ncx = parse_ncx(str(info.toc.ncx_path))

section = ncx.nav_points[1].children[0]  # First section of Chapter 1
opf_dir = info.opf_path.parent
html_path = str((opf_dir / section.file).resolve())

# Collect all anchors in this file for boundary detection
all_anchors = [section.anchor]

html = extract_content(html_path, section.anchor, all_anchors)
print(html[:300])
```

### Plaintext

```python
text = extract_content(
    html_path, section.anchor, all_anchors,
    output_format="plaintext",
)
print(text[:300])
```

### Markdown

```python
md = extract_content(
    html_path, section.anchor, all_anchors,
    output_format="markdown",
)
print(md[:300])
```

![Content Extraction](https://github.com/Abdullah-Wex/epubsage/blob/main/docs/screenshots/python-content.png?raw=true)

### Excluding Sections

```python
text = extract_content(
    html_path, chapter.anchor, toc_anchors,
    child_anchors=[c.anchor for c in chapter.children if c.anchor],
    exclude=["footnotes_anchor", "bibliography_anchor"],
    output_format="plaintext",
)
```

---

## Walk the TOC Tree

```python
from epubsage import inspect_epub, parse_ncx, classify_navpoint, classify_children

info = inspect_epub("book.epub")
ncx = parse_ncx(str(info.toc.ncx_path))

for pt in ncx.nav_points:
    pt.nav_type = classify_navpoint(pt)
classify_children(ncx.nav_points)


def walk(points, depth=0):
    for pt in points:
        indent = "  " * depth
        tag = pt.nav_type or "unknown"
        print(f"{indent}[{tag}] {pt.label} ({pt.file}#{pt.anchor})")
        walk(pt.children, depth + 1)


walk(ncx.nav_points)
```

---

## Batch Processing (CLI)

### Inspect all EPUBs

```bash
for file in *.epub; do
    echo "=== $file ==="
    epubsage inspect "$file"
    echo
done
```

### Extract TOCs to files

```bash
for file in *.epub; do
    name="${file%.epub}"
    epubsage toc "$file" > "${name}_toc.txt"
done
```

### Validate a library

```bash
for file in ~/Books/*.epub; do
    if epubsage validate "$file" 2>/dev/null; then
        echo "OK: $file"
    else
        echo "INVALID: $file"
    fi
done
```

---

## Error Handling

```python
from epubsage import inspect_epub, InvalidEpubError

try:
    info = inspect_epub("book.epub")
except InvalidEpubError as e:
    print(f"Invalid EPUB: {e}")
```

`InvalidEpubError` is raised for:
- File not found
- Not a valid ZIP file
- Zip bomb or zip slip detected
- No `.opf` file found
- OPF XML parsing failure

Non-error states (no exception):
- `info.toc.toc_type == "unknown"` — no TOC found
- `info.title is None` — no title in metadata

---

## See Also

- [API Reference](API.md)
- [CLI Reference](CLI.md)
