"""Regression tests for the nine parsing bugs fixed in v0.5.x.

Each test ships a synthetic XHTML fixture under ``tmp_path`` and exercises
one behaviour directly, avoiding dependencies on the user's EPUB library.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from epubsage.content import extract_content


def _write(tmp_path: Path, name: str, body: str) -> str:
    """Write a minimal XHTML document and return its path as a string."""
    doc = (
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        f'<body>{body}</body></html>'
    )
    p = tmp_path / name
    p.write_text(doc, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------- BUG-1 ---
def test_bug1_anchor_none_and_empty_return_whole_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.xhtml", "<p>First</p><p>Second</p>")
    assert (
        extract_content(path, None, [], output_format="plaintext")
        == extract_content(path, "", [], output_format="plaintext")
    )


def test_bug1_missing_body_does_not_crash(tmp_path: Path) -> None:
    # Root without <body>: the fallback path must not raise.
    p = tmp_path / "nobody.xhtml"
    p.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><p>loose</p></html>',
        encoding="utf-8",
    )
    out = extract_content(str(p), None, [], output_format="plaintext")
    assert "loose" in out


# ---------------------------------------------------------------- BUG-3 ---
def test_bug3_mathml_becomes_latex_in_markdown(tmp_path: Path) -> None:
    body = (
        '<p>inline '
        '<math xmlns="http://www.w3.org/1998/Math/MathML" alttext="x^2">'
        '<msup><mi>x</mi><mn>2</mn></msup></math>'
        ' end</p>'
    )
    path = _write(tmp_path, "mathml.xhtml", body)
    md = extract_content(path, None, [], output_format="markdown")
    assert "$x^2$" in md
    raw = extract_content(path, None, [], output_format=None)
    assert "ns0:" not in raw and "ns1:" not in raw
    assert "m:math" not in raw.lower()
    assert "<math" in raw


def test_bug3_mathml_no_alttext_falls_back_to_minimal_tex(
    tmp_path: Path,
) -> None:
    body = (
        '<p>'
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        '<mfrac><mn>1</mn><mn>2</mn></mfrac></math>'
        '</p>'
    )
    path = _write(tmp_path, "mathml2.xhtml", body)
    md = extract_content(path, None, [], output_format="markdown")
    assert "\\frac{1}{2}" in md


# ---------------------------------------------------------------- BUG-5 ---
@pytest.mark.parametrize("runs,expected_ticks", [(3, 4), (4, 5), (5, 6)])
def test_bug5_fence_length_exceeds_internal_backtick_run(
    tmp_path: Path, runs: int, expected_ticks: int,
) -> None:
    inner = "`" * runs
    body = f'<pre data-code-language="python">print({inner})</pre>'
    path = _write(tmp_path, "pre.xhtml", body)
    md = extract_content(path, None, [], output_format="markdown")
    ticks = re.findall(r"`{3,}", md)
    # Fence tokens should open and close at ``expected_ticks`` backticks.
    fence_tokens = [t for t in ticks if len(t) == expected_ticks]
    assert len(fence_tokens) == 2, md


# ---------------------------------------------------------------- BUG-7 ---
def test_bug7_merge_number_titles_off_by_default(tmp_path: Path) -> None:
    body = "<section><h1>2</h1><h1>The Module System</h1></section>"
    path = _write(tmp_path, "h.xhtml", body)
    off = extract_content(path, None, [], output_format="markdown")
    assert re.search(r"^#\s+2\s*$", off, re.M)
    on = extract_content(
        path, None, [], output_format="markdown",
        merge_number_titles=True,
    )
    assert re.search(r"^#\s+2\. The Module System", on, re.M)
    assert not re.search(r"^#\s+2\s*$", on, re.M)


# ---------------------------------------------------------------- BUG-9 ---
def test_bug9_subsup_digit_operator_to_unicode(tmp_path: Path) -> None:
    body = "<p>x<sub>1</sub> + y<sup>2</sup> = 10<sup>-3</sup></p>"
    path = _write(tmp_path, "ss.xhtml", body)
    md = extract_content(path, None, [], output_format="markdown")
    assert "x₁" in md
    assert "y²" in md
    assert "10⁻³" in md


def test_bug9_letter_subscript_is_not_converted(tmp_path: Path) -> None:
    body = "<p>g<sub>i</sub>(X)</p>"
    path = _write(tmp_path, "sl.xhtml", body)
    md = extract_content(path, None, [], output_format="markdown")
    # Letters outside the Unicode digit/operator map are left alone — markdownify
    # will still strip the tag, matching pre-fix behaviour (no regression).
    assert "gi(X)" in md.replace("*", "")


# ---------------------------------------------------------- img src path ---
def test_img_src_rewritten_to_absolute_path(tmp_path: Path) -> None:
    # Nested layout like Packt: HTML in Text/, images in sibling Images/.
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images").mkdir()
    img = tmp_path / "OEBPS" / "Images" / "fig1.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG magic
    html = tmp_path / "OEBPS" / "Text" / "ch1.xhtml"
    html.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        '<p>See <img src="../Images/fig1.png" alt="F"/></p>'
        '<p>External <img src="https://example.com/x.png"/></p>'
        "</body></html>"
    )
    raw = extract_content(str(html), None, [], output_format=None)
    # Relative src becomes absolute path pointing at the real file
    assert str(img.resolve()) in raw
    # External URL is left untouched
    assert "https://example.com/x.png" in raw


def test_img_srcset_rewritten(tmp_path: Path) -> None:
    (tmp_path / "OEBPS").mkdir()
    (tmp_path / "OEBPS" / "images").mkdir()
    a = tmp_path / "OEBPS" / "images" / "a.png"
    b = tmp_path / "OEBPS" / "images" / "b.png"
    a.write_bytes(b"x")
    b.write_bytes(b"y")
    html = tmp_path / "OEBPS" / "ch.xhtml"
    html.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        '<img src="images/a.png" srcset="images/a.png 1x, images/b.png 2x"/>'
        "</body></html>"
    )
    raw = extract_content(str(html), None, [], output_format=None)
    assert str(a.resolve()) in raw
    assert str(b.resolve()) in raw
    # Descriptors preserved
    assert "1x" in raw and "2x" in raw


# ---------------------------------------------------------------- BUG-2 ---
def test_bug2_stop_anchors_overrides_default_set(tmp_path: Path) -> None:
    # Target <h1 id="t"> with a descendant id ``idx`` inside the first <p>.
    # Default behaviour treats ``idx`` as a boundary and truncates.
    # With stop_anchors=["end"] only the ``end`` heading counts as a boundary.
    body = (
        '<h1 id="t">Target</h1>'
        '<p>Intro with <span id="idx">cross-ref</span> inside.</p>'
        '<p>More prose.</p>'
        '<h1 id="end">Next</h1>'
        '<p>Next section.</p>'
    )
    path = _write(tmp_path, "b2.xhtml", body)
    toc_anchors = ["t", "idx", "end"]

    truncated = extract_content(
        path, "t", toc_anchors, output_format="plaintext",
    )
    full = extract_content(
        path, "t", toc_anchors, output_format="plaintext",
        stop_anchors=["end"],
    )
    assert "More prose." in full
    assert "More prose." not in truncated
    assert "Next section." not in full
