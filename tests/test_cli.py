"""Tests for the unified CLI output contract (--json, streams, exit codes)."""

from __future__ import annotations

import json
from pathlib import Path

from al_warraq.cli import app
from typer.testing import CliRunner

from tests.test_search import _make_epub

runner = CliRunner()


def _out(tmp_path: Path) -> str:
    return str(tmp_path / "out")


def test_inspect_json_shape(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    result = runner.invoke(app, ["inspect", str(epub), "-o", _out(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["version"] == "2.0"
    assert data["title"] == "Test Book"
    assert data["toc"]["type"] == "ncx"
    assert len(data["hash"]) == 16


def test_validate_json_valid(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    result = runner.invoke(app, ["validate", str(epub), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["valid"] is True


def test_validate_json_invalid_exits_1(tmp_path: Path) -> None:
    missing = tmp_path / "missing.epub"
    result = runner.invoke(app, ["validate", str(missing), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["valid"] is False
    assert "error" in data


def test_toc_json_tree(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    result = runner.invoke(app, ["toc", str(epub), "-o", _out(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["doc_title"] == "Test Book"
    labels = [pt["label"] for pt in data["nav_points"]]
    assert "Chapter One" in labels
    chapter_one = data["nav_points"][labels.index("Chapter One")]
    assert chapter_one["children"][0]["anchor"] == "sec"


def test_search_json_results(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    result = runner.invoke(
        app, ["search", str(epub), "redux", "-o", _out(tmp_path), "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["query"] == "redux"
    assert data["total"] >= 1
    top = data["results"][0]
    assert set(top) >= {"score", "breadcrumb", "file", "anchor"}


def test_content_json_and_raw_stdout(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    result = runner.invoke(
        app,
        ["content", str(epub), "-a", "sec", "-p", "plaintext",
         "-o", _out(tmp_path), "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["anchor"] == "sec"
    assert "Redux" in data["content"]

    raw = runner.invoke(
        app,
        ["content", str(epub), "-a", "sec", "-p", "plaintext", "-o", _out(tmp_path)],
    )
    assert raw.exit_code == 0
    assert "Redux manages global state" in raw.stdout
    assert "Error" not in raw.stdout


def test_error_is_single_line_no_help_dump(tmp_path: Path) -> None:
    result = runner.invoke(app, ["inspect", str(tmp_path / "missing.epub")])
    assert result.exit_code == 1
    combined = result.output
    assert "Error:" in combined
    assert "Usage:" not in combined  # no full help dump after errors
    assert "--help" in combined  # but a hint is present


def test_missing_path_is_usage_error() -> None:
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 2
    assert "Usage:" not in result.output


def test_search_no_match_exits_zero(tmp_path: Path) -> None:
    epub = _make_epub(tmp_path)
    result = runner.invoke(
        app, ["search", str(epub), "zzznope", "-o", _out(tmp_path)],
    )
    assert result.exit_code == 0
