"""Content extraction by TOC anchor reference."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from .exceptions import InvalidEpubError

if TYPE_CHECKING:
    from .ncx import NavPoint

XHTML_NS = "http://www.w3.org/1999/xhtml"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
EPUB_OPS_NS = "http://www.idpf.org/2007/ops"

# Register XHTML namespace with empty prefix so serialization
# outputs <div> instead of <html:div> or <ns0:div>.
ET.register_namespace("", XHTML_NS)
# Stable prefixes for MathML and EPUB ops so ElementTree does not auto-assign
# ``ns1:`` / ``ns2:`` at serialization time.
ET.register_namespace("m", MATHML_NS)
ET.register_namespace("epub", EPUB_OPS_NS)

# Strip both default ``xmlns="..."`` and prefixed ``xmlns:xyz="..."`` attrs.
_XMLNS_RE = re.compile(r'\s+xmlns(:\w+)?="[^"]*"')
# Drop the ``m:`` MathML prefix so output is HTML5-native ``<math>...</math>``.
_MATHML_PREFIX_RE = re.compile(r"(</?)m:([a-zA-Z][\w-]*)")
# Drop the ``epub:`` ops prefix on attributes (e.g. ``epub:type="chapter"``
# → ``type="chapter"``) so markup reads as plain HTML5.
_EPUB_ATTR_RE = re.compile(r'\sepub:([a-zA-Z][\w-]*)=')
# Collapse any remaining auto-assigned ``nsN:`` prefix on tags or attributes.
_GENERIC_NS_RE = re.compile(r"(</?|\s)ns\d+:([a-zA-Z][\w-]*)")


def extract_content(
    html_path: str,
    anchor: str | None,
    toc_anchors: list[str],
    child_anchors: list[str] | None = None,
    exclude: list[str] | None = None,
    output_format: str | None = None,
    *,
    merge_number_titles: bool = False,
    stop_anchors: list[str] | None = None,
) -> str:
    """Extract HTML content for a TOC entry.

    Args:
        html_path: Path to the chapter/section HTML file.
        anchor: Element ID to start from; ``None`` or empty string returns the
            entire file body.
        toc_anchors: All TOC anchor IDs in this file (for boundary detection).
        child_anchors: Anchors that are children of the target in the TOC
            tree. These are NOT treated as stop boundaries.
        exclude: Anchor IDs whose sections should be excluded.
        output_format: ``"plaintext"``, ``"markdown"`` or ``None`` (raw HTML).
        merge_number_titles: When true and ``output_format="markdown"``, merge
            adjacent same-level headings where one is a bare number (Packt
            style: ``<h1>2</h1><h1>Title</h1>`` → ``## 2. Title``).
        stop_anchors: Explicit set of anchors to treat as section boundaries.
            When given it replaces the default ``toc_anchors - {anchor} -
            child_anchors`` computation, which lets callers avoid false
            positives on publishers that embed TOC anchors in mid-section
            prose (e.g. Packt's ``_idParaDest-*`` pattern).

    Returns:
        Content as a string in the requested format.
    """
    try:
        tree = ET.parse(html_path)  # noqa: S314
    except ET.ParseError as e:
        raise InvalidEpubError(f"Failed to parse HTML: {e}") from e

    root = tree.getroot()
    exclude_set = set(exclude) if exclude else set()
    child_set = set(child_anchors) if child_anchors else set()
    # Stop boundaries: explicit stop_anchors override the default computation.
    if stop_anchors is not None:
        anchor_set = set(stop_anchors) - child_set - (
            {anchor} if anchor else set()
        )
    elif anchor:
        anchor_set = set(toc_anchors) - {anchor} - child_set
    else:
        anchor_set = set(toc_anchors)

    if not anchor:
        # Entire file — get body children
        body = _find_body(root)
        elements = [root] if body is None else list(body)
    else:
        # Find the anchor element and collect its section
        target = _find_by_id(root, anchor)
        if target is None:
            raise InvalidEpubError(f"Anchor '{anchor}' not found in {html_path}")

        parent_map = _build_parent_map(root)

        # Walk up to find the right collection level:
        # the ancestor whose direct children contain other TOC anchors
        container, start_child = _find_collection_level(
            target, parent_map, anchor_set,
        )
        if container is None:
            elements = [target]
        else:
            elements = _collect_section(container, start_child, anchor_set)

    if exclude_set:
        all_toc_ids = set(toc_anchors)
        elements = _remove_excluded(elements, exclude_set, all_toc_ids)

    # Rewrite resource references (img/source/object/embed/svg image) to
    # absolute filesystem paths so consumers of the output can load the
    # assets without knowing the EPUB's internal layout.
    html_dir = Path(html_path).parent
    for el in elements:
        _absolutize_resources(el, html_dir)

    if output_format == "plaintext":
        return _elements_to_text(elements)
    if output_format == "markdown":
        return _elements_to_markdown(
            elements, merge_number_titles=merge_number_titles,
        )
    return _serialize(elements)


def _find_body(root: ET.Element) -> ET.Element | None:
    """Find <body> element."""
    for tag in [f"{{{XHTML_NS}}}body", "body"]:
        body = root.find(f".//{tag}")
        if body is not None:
            return body
    return None


def _find_by_id(root: ET.Element, target_id: str) -> ET.Element | None:
    """Find element with matching id attribute (recursive)."""
    for el in root.iter():
        if el.get("id") == target_id:
            return el
    return None


def _build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    """Build child → parent mapping."""
    return {child: parent for parent in root.iter() for child in parent}


def _find_collection_level(
    target: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
    stop_ids: set[str],
) -> tuple[ET.Element | None, ET.Element]:
    """Find the right DOM level to collect siblings from.

    Walks up from ``target`` looking for a parent whose direct children
    contain other TOC anchor IDs. When such a parent is found, returns
    ``(parent, current)`` — ``current`` is the parent's child that contains
    ``target`` (the start of the section).

    When no boundary is found (either ``stop_ids`` is empty or the target is
    the last section in the document), falls back to the outermost sensible
    container so the whole remaining document from ``target`` onward is
    returned rather than just the target element in isolation.
    """
    current = target
    last_parent: ET.Element | None = None
    while current in parent_map:
        parent = parent_map[current]
        for child in parent:
            if child is not current and _contains_id(child, stop_ids):
                return parent, current
        last_parent = parent
        current = parent
    # Reached the tree root without finding a boundary. Fall back to the
    # outermost parent we walked through — typically <html>, whose child is
    # the ancestor chain containing target. Collecting from that child gives
    # "everything from target's top-level ancestor onward", which matches the
    # intent when there is no explicit section boundary ahead.
    if last_parent is not None:
        # ``current`` is now the root; the target's highest non-root ancestor
        # is the last element we stepped through before hitting root.
        # Re-derive it by walking down the parent chain.
        start = target
        while parent_map.get(start) is not last_parent:
            if start not in parent_map:
                break
            start = parent_map[start]
        return last_parent, start
    return None, target


def _collect_section(
    parent: ET.Element, target: ET.Element, stop_ids: set[str],
) -> list[ET.Element]:
    """Collect target + following siblings until a stop boundary."""
    elements: list[ET.Element] = []
    found = False

    for child in parent:
        if child is target:
            found = True

        if found:
            # Stop if this sibling contains a TOC anchor (boundary)
            if child is not target and _contains_id(child, stop_ids):
                break
            elements.append(child)

    return elements


def _remove_excluded(
    elements: list[ET.Element],
    exclude_ids: set[str],
    toc_anchor_ids: set[str],
) -> list[ET.Element]:
    """Remove elements that belong to excluded sections."""
    result: list[ET.Element] = []
    skipping = False

    for el in elements:
        el_id = el.get("id", "")

        if el_id in exclude_ids or _contains_id(el, exclude_ids):
            skipping = True
            continue

        if skipping:
            # Stop skipping when we hit a non-excluded TOC anchor
            if el_id in toc_anchor_ids or _contains_id(el, toc_anchor_ids - exclude_ids):
                skipping = False
                result.append(el)
            # else: still in excluded section, skip
        else:
            result.append(el)

    return result


def _contains_id(element: ET.Element, id_set: set[str]) -> bool:
    """Check if element or any descendant has an id in the set."""
    if element.get("id", "") in id_set:
        return True
    return any(child.get("id", "") in id_set for child in element.iter())


_BLOCK_TAGS = frozenset({
    "div", "p", "section", "article", "blockquote", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "tr", "figure", "figcaption", "header", "footer", "nav",
})
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_SKIP_TAGS = frozenset({"script", "style", "head"})
_NEWLINE_RE = re.compile(r"\n{3,}")
_SPACES_RE = re.compile(r"[^\S\n]+")
_WS_RUN_RE = re.compile(r"\s+")
_PRE_START = "\x00PRE\x00"
_PRE_END = "\x01PRE\x01"


# Attribute names that hold a single resource reference per element.
_RESOURCE_ATTRS = ("src", "href", "data")
# xlink:href on SVG <image> elements.
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def _absolutize_resources(el: ET.Element, html_dir: Path) -> None:
    """Rewrite relative resource references to absolute filesystem paths.

    Resolves every ``src`` / ``href`` / ``data`` / ``xlink:href`` attribute on
    resource-bearing elements (``<img>``, ``<source>``, ``<image>`` in SVG,
    ``<object>``, ``<embed>``, ``<video>``, ``<audio>``) against ``html_dir``.
    Skips values carrying a URI scheme (``http``, ``https``, ``data``, …) and
    protocol-relative (``//…``) references.

    Also rewrites ``srcset`` when present: each comma-separated candidate is
    resolved independently while preserving its descriptor (``1x``, ``2x``,
    ``640w`` etc.).
    """
    targets = {"img", "source", "image", "object", "embed", "video", "audio"}
    for node in el.iter():
        tag = _tag_local(node)
        if tag not in targets:
            continue
        for attr in _RESOURCE_ATTRS:
            raw = node.get(attr)
            if raw:
                resolved = _resolve_ref(raw, html_dir)
                if resolved is not None:
                    node.set(attr, resolved)
        xlink = node.get(_XLINK_HREF)
        if xlink:
            resolved = _resolve_ref(xlink, html_dir)
            if resolved is not None:
                node.set(_XLINK_HREF, resolved)
        srcset = node.get("srcset")
        if srcset:
            node.set("srcset", _rewrite_srcset(srcset, html_dir))


def _resolve_ref(raw: str, html_dir: Path) -> str | None:
    """Return an absolute path for ``raw`` or None when it should be left
    alone (absolute URL, data URI, empty, protocol-relative)."""
    value = raw.strip()
    if not value:
        return None
    if value.startswith("#"):
        return None
    if value.startswith("//"):
        return None
    if _SCHEME_RE.match(value):
        return None
    try:
        return str((html_dir / value).resolve())
    except OSError:
        return None


def _rewrite_srcset(srcset: str, html_dir: Path) -> str:
    out_parts: list[str] = []
    for candidate in srcset.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        bits = candidate.split(None, 1)
        url = bits[0]
        descriptor = f" {bits[1]}" if len(bits) > 1 else ""
        resolved = _resolve_ref(url, html_dir)
        out_parts.append(f"{resolved or url}{descriptor}")
    return ", ".join(out_parts)


def _collapse_inline_whitespace(el: ET.Element) -> None:
    """Collapse source-level whitespace runs in element text/tail to a single
    space, matching how browsers render HTML flow content.

    Skips descendants of ``<pre>`` whose whitespace is significant. Operates
    recursively and in place; callers should deep-copy first if they don't
    want to mutate the input.
    """
    for child in list(el):
        tag = _tag_local(child)
        if tag == "pre":
            # <pre> whitespace is significant — don't touch text/tail here.
            # Still normalise the tail so surrounding flow content behaves.
            if child.tail:
                child.tail = _WS_RUN_RE.sub(" ", child.tail)
            continue
        if child.text:
            child.text = _WS_RUN_RE.sub(" ", child.text)
        if child.tail:
            child.tail = _WS_RUN_RE.sub(" ", child.tail)
        _collapse_inline_whitespace(child)
    # Also normalise the parent's own leading text (el.text), which would be
    # missed by the loop above (it only touches children's text/tail).
    if el.text and _tag_local(el) != "pre":
        el.text = _WS_RUN_RE.sub(" ", el.text)


def _tag_local(el: ET.Element) -> str:
    """Get local tag name, stripping namespace."""
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return str(tag)


def _elements_to_text(elements: list[ET.Element]) -> str:
    """Convert element list to plain text with proper spacing."""
    import copy
    # Deep-copy + normalize inline whitespace so HTML source newlines within
    # a paragraph don't leak into the plaintext output (browsers collapse
    # them; we should too).
    elements = [copy.deepcopy(el) for el in elements]
    for el in elements:
        _collapse_inline_whitespace(el)

    parts: list[str] = []
    for el in elements:
        _walk(el, parts, list_stack=[])
    raw = "".join(parts)
    # Collapse spaces outside <pre> blocks (sentinels protect pre content)
    segments = raw.split(_PRE_START)
    result_parts: list[str] = []
    for i, seg in enumerate(segments):
        if i == 0:
            # Before first <pre> — collapse spaces
            result_parts.append(_SPACES_RE.sub(" ", seg))
        else:
            # Contains _PRE_END — split into pre content and rest
            pre_content, _, after = seg.partition(_PRE_END)
            result_parts.append(pre_content)
            result_parts.append(_SPACES_RE.sub(" ", after))
    raw = "".join(result_parts)
    raw = _NEWLINE_RE.sub("\n\n", raw)
    return raw.strip()


def _walk(
    el: ET.Element,
    parts: list[str],
    list_stack: list[list[str | int]],
    inside_li: bool = False,
) -> None:
    """Recursively walk an element, appending text to parts.

    ``list_stack`` tracks nesting: each entry is ``[tag, counter]``
    where counter increments for ``<ol>`` items.
    """
    tag = _tag_local(el)

    if tag in _SKIP_TAGS:
        return

    # <pre> blocks: preserve whitespace as-is (skip normal recursion)
    if tag == "pre":
        parts.append("\n\n")
        parts.append(_PRE_START)
        parts.append(_pre_text(el).rstrip())
        parts.append(_PRE_END)
        parts.append("\n\n")
        return

    is_block = tag in _BLOCK_TAGS
    is_heading = tag in _HEADING_TAGS
    is_list = tag in ("ul", "ol")
    is_li = tag == "li"
    is_br = tag == "br"

    # Pre-element spacing (suppress for blocks inside <li>)
    if is_heading:
        parts.append("\n\n")
    elif is_block and not inside_li:
        parts.append("\n")

    if is_br:
        parts.append("\n")

    # List item prefix
    if is_li and list_stack:
        indent = "  " * (len(list_stack) - 1)
        parent_type = list_stack[-1][0]
        if parent_type == "ol":
            list_stack[-1][1] = int(list_stack[-1][1]) + 1  # type: ignore[arg-type]
            parts.append(f"{indent}{list_stack[-1][1]}. ")
        else:
            parts.append(f"{indent}- ")

    # Push list context
    if is_list:
        list_stack.append([tag, 0])

    # Element's own text (skip whitespace-only in block contexts)
    if el.text:
        text = el.text
        if not (is_block and text.strip() == ""):
            parts.append(text)

    # Recurse into children
    in_li = inside_li or is_li
    for child in el:
        _walk(child, parts, list_stack, inside_li=in_li)
        # Child's tail text (skip whitespace-only between blocks)
        if child.tail:
            tail = child.tail
            if not (is_block and tail.strip() == ""):
                parts.append(tail)

    # Pop list context
    if is_list:
        list_stack.pop()

    # Post-element spacing
    if is_heading or is_li or (is_block and not inside_li):
        parts.append("\n")


_MATH_TAG = f"{{{MATHML_NS}}}math"

# Unicode subscript / superscript coverage (digit + common operators).
# Letters have incomplete coverage in Unicode so we leave those alone.
_SUB_MAP = str.maketrans(
    "0123456789+-=()",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎",
)
_SUP_MAP = str.maketrans(
    "0123456789+-=()n",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ",
)


def _rewrite_subsup(parent: ET.Element) -> None:
    """Convert ``<sub>`` / ``<sup>`` with translatable content to Unicode.

    markdownify strips both tags by default (not in its ``convert`` list), so
    ``<i>g</i><sub>i</sub>`` flattens to ``*g*i`` — the subscript relation is
    lost. This pre-pass substitutes digit / operator content for a lossless
    character-level fix. Letters are skipped because Unicode sub/sup coverage
    is incomplete and would produce worse output.
    """
    for child in list(parent):
        _rewrite_subsup(child)
        tag = _tag_local(child)
        if tag not in ("sub", "sup"):
            continue
        text = "".join(child.itertext())
        stripped = text.strip()
        if not stripped:
            continue
        mapping = _SUB_MAP if tag == "sub" else _SUP_MAP
        # ``str.maketrans`` returns an ordinal-keyed dict.
        if not all(ord(c) in mapping for c in stripped):
            continue
        translated = text.translate(mapping)
        _replace_with_text(parent, child, translated)


def _replace_with_text(
    parent: ET.Element, child: ET.Element, text: str,
) -> None:
    """Remove ``child`` and splice ``text`` in its place (preserving tail)."""
    idx = list(parent).index(child)
    tail = child.tail or ""
    parent.remove(child)
    payload = text + tail
    if idx == 0:
        parent.text = (parent.text or "") + payload
    else:
        prev = list(parent)[idx - 1]
        prev.tail = (prev.tail or "") + payload


def _rewrite_mathml(parent: ET.Element) -> None:
    """Replace every ``<math>`` descendant with a ``$...$`` / ``$$...$$`` span.

    Uses the ``alttext`` attribute when present; otherwise renders a minimal
    LaTeX approximation of the MathML subtree. Run before markdownify so
    equations do not get silently dropped along with their unknown tags.
    """
    # Walk with explicit parent tracking so we can splice replacements in.
    for child in list(parent):
        _rewrite_mathml(child)
        if _tag_local(child) == "math" or child.tag == _MATH_TAG:
            _replace_math_in_parent(parent, child)


def _replace_math_in_parent(parent: ET.Element, math: ET.Element) -> None:
    display = (math.get("display") == "block")
    alttext = math.get("alttext") or _mathml_to_tex(math)
    if not alttext.strip():
        return
    delim = "$$" if display else "$"
    idx = list(parent).index(math)
    tail = math.tail or ""
    span = ET.Element(f"{{{XHTML_NS}}}span")
    span.text = f"{delim}{alttext}{delim}"
    span.tail = tail
    parent.remove(math)
    parent.insert(idx, span)


def _mathml_to_tex(el: ET.Element) -> str:
    """Minimal MathML → LaTeX mapping for common atomic elements."""
    tag = _tag_local(el)
    if tag in ("mi", "mn", "mo", "mtext"):
        return (el.text or "").strip()
    if tag == "mrow":
        return "".join(_mathml_to_tex(c) for c in el)
    if tag == "msub":
        kids = list(el)
        if len(kids) >= 2:
            return f"{_mathml_to_tex(kids[0])}_{{{_mathml_to_tex(kids[1])}}}"
    if tag == "msup":
        kids = list(el)
        if len(kids) >= 2:
            return f"{_mathml_to_tex(kids[0])}^{{{_mathml_to_tex(kids[1])}}}"
    if tag == "msubsup":
        kids = list(el)
        if len(kids) >= 3:
            base = _mathml_to_tex(kids[0])
            sub = _mathml_to_tex(kids[1])
            sup = _mathml_to_tex(kids[2])
            return f"{base}_{{{sub}}}^{{{sup}}}"
    if tag == "mfrac":
        kids = list(el)
        if len(kids) >= 2:
            return (
                f"\\frac{{{_mathml_to_tex(kids[0])}}}"
                f"{{{_mathml_to_tex(kids[1])}}}"
            )
    if tag == "msqrt":
        return f"\\sqrt{{{''.join(_mathml_to_tex(c) for c in el)}}}"
    if tag == "mstyle" or tag == "math":
        return "".join(_mathml_to_tex(c) for c in el)
    # Fallback: concatenate any text content.
    return "".join(el.itertext()).strip()


def _merge_numbered_headings(
    elements: list[ET.Element],
) -> list[ET.Element]:
    """Merge adjacent same-level headings where one is a bare number.

    Packt books author chapter numbering and title as two sibling ``<h1>``
    elements (``<h1>2</h1><h1>The Module System</h1>``). This fuses them into
    a single heading preserving any ``id`` from the numeric element. Operates
    recursively on the whole tree since the sibling pair is usually wrapped
    in a ``<section>`` or similar container.
    """
    for el in elements:
        _merge_numbered_headings_in_place(el)
    return _merge_sibling_headings(elements)


def _merge_numbered_headings_in_place(parent: ET.Element) -> None:
    """Recursive in-place merge on a single element's descendants."""
    # Depth-first: merge inside each child first, then among siblings.
    for child in list(parent):
        _merge_numbered_headings_in_place(child)
    kept = _merge_sibling_headings(list(parent))
    # Re-attach the kept list under parent
    for child in list(parent):
        parent.remove(child)
    for child in kept:
        parent.append(child)


def _merge_sibling_headings(
    siblings: list[ET.Element],
) -> list[ET.Element]:
    """Merge adjacent numeric/title heading pairs in a single sibling list."""
    out: list[ET.Element] = []
    i = 0
    while i < len(siblings):
        cur = siblings[i]
        nxt = siblings[i + 1] if i + 1 < len(siblings) else None
        if (
            nxt is not None
            and _tag_local(cur) in _HEADING_TAGS
            and _tag_local(cur) == _tag_local(nxt)
            and (cur.text or "").strip().isdigit()
            and not list(cur)
            and (not cur.tail or not cur.tail.strip())
        ):
            number = (cur.text or "").strip()
            existing = (nxt.text or "").lstrip()
            nxt.text = f"{number}. {existing}"
            if cur.get("id") and not nxt.get("id"):
                nxt.set("id", cur.get("id", ""))
            out.append(nxt)
            i += 2
        else:
            out.append(cur)
            i += 1
    return out


def _elements_to_markdown(
    elements: list[ET.Element], *, merge_number_titles: bool = False,
) -> str:
    """Convert element list to Markdown via markdownify."""
    import copy

    from markdownify import markdownify as md

    # Deep copy to avoid mutating caller's elements
    elements = [copy.deepcopy(el) for el in elements]

    # Collapse source-level whitespace inside flow content so browser-rendered
    # single paragraphs don't come out with embedded newlines in markdown.
    for el in elements:
        _collapse_inline_whitespace(el)

    # Rewrite MathML to ``$...$`` / ``$$...$$`` before markdownify drops it.
    for el in elements:
        _rewrite_mathml(el)

    # Translatable ``<sub>``/``<sup>`` (digits + operators) → Unicode so the
    # subscript/superscript relation survives markdownify's tag stripping.
    for el in elements:
        _rewrite_subsup(el)

    if merge_number_titles:
        elements = _merge_numbered_headings(elements)

    # Extract all <pre> blocks and replace with markers.
    # This ensures code blocks render correctly even inside <table> cells.
    pre_blocks: list[tuple[str, str]] = []
    for el in elements:
        # Handle a top-level <pre> element (``_extract_pre_blocks`` only
        # processes descendants).
        if _tag_local(el) == "pre":
            lang = el.get("data-code-language", "")
            text = _pre_text(el).strip()
            idx = len(pre_blocks)
            pre_blocks.append((lang, text))
            el.clear()
            el.tag = f"{{{XHTML_NS}}}p"
            el.text = f"CODEBLOCK{idx}ENDBLOCK"
        else:
            _extract_pre_blocks(el, pre_blocks)

    # Serialize and convert (no <pre> elements remain)
    html = _serialize(elements)
    result = md(html, heading_style="ATX")

    # Replace markers with fenced code blocks.
    # Fence length must exceed the longest backtick run inside ``text``
    # (CommonMark) so literal triple-backticks in the code do not break parity.
    for i, (lang, text) in enumerate(pre_blocks):
        marker = f"CODEBLOCK{i}ENDBLOCK"
        max_run = max(
            (len(m.group()) for m in re.finditer(r"`+", text)), default=0,
        )
        tick = "`" * max(3, max_run + 1)
        fence = f"\n\n{tick}{lang}\n{text}\n{tick}\n\n"
        result = result.replace(marker, fence)

    result = _NEWLINE_RE.sub("\n\n", result)
    return result.strip()


def _extract_pre_blocks(
    el: ET.Element,
    blocks: list[tuple[str, str]],
) -> None:
    """Replace <pre> elements with markers, collecting their content."""
    for child in list(el):
        tag = _tag_local(child)
        if tag == "pre":
            lang = child.get("data-code-language", "")
            text = _pre_text(child).strip()
            idx = len(blocks)
            blocks.append((lang, text))
            # Replace <pre> with a marker paragraph
            child.clear()
            child.tag = "p"
            child.text = f"CODEBLOCK{idx}ENDBLOCK"
        else:
            _extract_pre_blocks(child, blocks)


def _pre_text(el: ET.Element) -> str:
    """Extract text from element, preserving <img> alt text as [alt]."""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        tag = _tag_local(child)
        if tag == "img":
            alt = child.get("alt", "")
            if alt:
                parts.append(f"[{alt}]")
        else:
            parts.append(_pre_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _serialize(elements: list[ET.Element]) -> str:
    """Serialize list of elements to HTML string."""
    parts: list[str] = []
    for el in elements:
        text = ET.tostring(el, encoding="unicode", method="html")
        text = _XMLNS_RE.sub("", text)
        text = _MATHML_PREFIX_RE.sub(r"\1\2", text)
        text = _EPUB_ATTR_RE.sub(r" data-epub-\1=", text)
        text = _GENERIC_NS_RE.sub(r"\1\2", text)
        parts.append(text)
    return "\n".join(parts)


@dataclass
class Section:
    """A single extracted section from an ``extract_all_sections`` call."""

    anchor: str | None
    label: str
    content: str


def extract_all_sections(
    nav_points: list[NavPoint],
    html_path: str,
    *,
    output_format: str | None = None,
    merge_number_titles: bool = False,
) -> list[Section]:
    """Extract every TOC section under ``nav_points`` exactly once.

    Walks the NavPoint tree depth-first and calls ``extract_content`` per node
    with a correctly scoped ``child_anchors`` set so a parent section's output
    does not duplicate its children's content.

    ``nav_points`` should be pre-filtered to a single HTML file (the caller
    decides how to partition its TOC). Each ``Section.content`` is returned in
    the requested ``output_format``.
    """
    flat: list[NavPoint] = []
    seen: set[int] = set()
    _flatten_into(nav_points, flat, seen)
    toc_anchors = [pt.anchor for pt in flat if pt.anchor]

    # Pre-compute per-node stop anchors: the flattened descendants of every
    # following TOC sibling (at each level up the ancestry chain). These are
    # the real section boundaries, independent of stray mid-prose anchors.
    stops_by_id = _compute_stop_anchors(nav_points)

    sections: list[Section] = []
    for pt in flat:
        child_anchors = _collect_descendant_anchors(pt.children)
        stop_anchors = stops_by_id.get(id(pt), [])
        content = extract_content(
            html_path,
            pt.anchor,
            toc_anchors,
            child_anchors=child_anchors,
            output_format=output_format,
            merge_number_titles=merge_number_titles,
            stop_anchors=stop_anchors,
        )
        sections.append(Section(anchor=pt.anchor, label=pt.label, content=content))
    return sections


def _compute_stop_anchors(
    roots: list[NavPoint],
) -> dict[int, list[str]]:
    """Build a ``{id(NavPoint): [stop_anchors]}`` map for a NavPoint forest.

    Stops for a node are the anchors of all later siblings (plus every later
    sibling's descendants) at each level of the ancestry chain, filtered to
    the node's own ``file``. Filtering by file is essential because some
    publishers (e.g. Manning) restart paragraph numbering per chapter so
    anchor IDs collide across files.
    """
    out: dict[int, list[str]] = {}

    def walk(siblings: list[NavPoint], tail_siblings: list[NavPoint]) -> None:
        # ``tail_siblings`` = following-sibling NavPoints inherited from each
        # ancestor. We carry the NavPoints (not their anchors) so the
        # file-filter can be applied per-node below.
        for i, pt in enumerate(siblings):
            later = siblings[i + 1 :]
            # Compute same-file anchors for this node.
            stops: list[str] = []
            for sib in later:
                _collect_same_file_anchors_local(sib, pt.file, stops)
            for sib in tail_siblings:
                _collect_same_file_anchors_local(sib, pt.file, stops)
            out[id(pt)] = stops
            # Children inherit: our following siblings + ancestors' tail.
            walk(pt.children, later + tail_siblings)

    walk(roots, [])
    return out


def _collect_same_file_anchors_local(
    pt: NavPoint, file: str, out: list[str],
) -> None:
    """Append ``pt`` and its descendants' anchors iff they are in ``file``."""
    if pt.anchor and pt.file == file:
        out.append(pt.anchor)
    for child in pt.children:
        _collect_same_file_anchors_local(child, file, out)


def _flatten_into(
    points: list[NavPoint], out: list[NavPoint], seen: set[int],
) -> None:
    for pt in points:
        if id(pt) in seen:
            continue
        seen.add(id(pt))
        out.append(pt)
        _flatten_into(pt.children, out, seen)


def _collect_descendant_anchors(points: list[NavPoint]) -> list[str]:
    out: list[str] = []
    for pt in points:
        if pt.anchor:
            out.append(pt.anchor)
        out.extend(_collect_descendant_anchors(pt.children))
    return out
