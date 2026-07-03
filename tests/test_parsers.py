"""Regression tests for OPF, NCX, NAV parsers (BUG-4, BUG-6, BUG-8)."""
from __future__ import annotations

from pathlib import Path

from al_warraq import Section, extract_all_sections
from al_warraq.nav import parse_nav
from al_warraq.ncx import parse_ncx
from al_warraq.opf import parse_opf


# ---------------------------------------------------------------- BUG-4 ---
def test_bug4_nav_href_resolved_against_nav_dir(tmp_path: Path) -> None:
    nested = tmp_path / "OEBPS" / "Text"
    nested.mkdir(parents=True)
    chapter = nested / "Chapter_1.xhtml"
    chapter.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>',
    )
    nav_path = nested / "nav.xhtml"
    nav_path.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops">'
        '<body><nav epub:type="toc"><ol>'
        '<li><a href="Chapter_1.xhtml">Ch 1</a></li>'
        '</ol></nav></body></html>'
    )
    points = parse_nav(str(nav_path))
    assert len(points) == 1
    assert points[0].abs_file is not None
    assert Path(points[0].abs_file) == chapter.resolve()


def test_bug4_ncx_src_resolved_against_ncx_dir(tmp_path: Path) -> None:
    nested = tmp_path / "OEBPS"
    nested.mkdir()
    chapter = nested / "ch1.xhtml"
    chapter.write_text("<html/>")
    ncx_path = nested / "toc.ncx"
    ncx_path.write_text(
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">'
        '<docTitle><text>X</text></docTitle>'
        '<navMap><navPoint id="a" playOrder="1">'
        '<navLabel><text>L</text></navLabel>'
        '<content src="ch1.xhtml#top"/>'
        "</navPoint></navMap></ncx>"
    )
    ncx = parse_ncx(str(ncx_path))
    assert ncx.nav_points[0].abs_file is not None
    assert Path(ncx.nav_points[0].abs_file) == chapter.resolve()
    assert ncx.nav_points[0].anchor == "top"


# ---------------------------------------------------------------- BUG-6 ---
def test_bug6_dublin_core_html_entities_unescaped(tmp_path: Path) -> None:
    opf = tmp_path / "content.opf"
    opf.write_text(
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:title>Book &amp; Tale</dc:title>"
        "<dc:publisher>O&#8217;Reilly Media, Inc.</dc:publisher>"
        "<dc:creator>Foster &amp; Tom</dc:creator>"
        "</metadata><manifest/></package>"
    )
    info = parse_opf(str(opf), str(tmp_path))
    assert info.title == "Book & Tale"
    assert info.publisher is not None
    assert "’" in info.publisher  # right single quotation mark  # noqa: RUF001
    assert info.creator == "Foster & Tom"


# ---------------------------------------------------------------- BUG-8 ---
def test_bug8_extract_all_sections_no_duplication(tmp_path: Path) -> None:
    # One XHTML file with four sections anchored as "s1".."s4".
    chapter = tmp_path / "ch.xhtml"
    chapter.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        '<h1 id="s1">Section 1</h1><p>para1</p>'
        '<h1 id="s2">Section 2</h1><p>para2</p>'
        '<h1 id="s3">Section 3</h1><p>para3</p>'
        '<h1 id="s4">Section 4</h1><p>para4</p>'
        "</body></html>"
    )
    # Build NCX pointing at that file.
    ncx_path = tmp_path / "toc.ncx"
    navpoints = "".join(
        f'<navPoint id="p{n}" playOrder="{n}">'
        f'<navLabel><text>Section {n}</text></navLabel>'
        f'<content src="ch.xhtml#s{n}"/></navPoint>'
        for n in range(1, 5)
    )
    ncx_path.write_text(
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">'
        '<docTitle><text>x</text></docTitle>'
        f"<navMap>{navpoints}</navMap></ncx>"
    )
    ncx = parse_ncx(str(ncx_path))
    sections = extract_all_sections(
        ncx.nav_points, str(chapter), output_format="plaintext",
    )
    assert len(sections) == 4
    assert all(isinstance(s, Section) for s in sections)
    # Each section should contain its own paragraph exactly once, not bleed
    # into others.
    assert "para1" in sections[0].content
    assert "para2" not in sections[0].content
    assert "para2" in sections[1].content
    assert "para4" in sections[3].content
