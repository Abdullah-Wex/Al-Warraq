"""Tests for per-book session history (al_warraq.tui.history)."""

from __future__ import annotations

from pathlib import Path

from al_warraq.tui.history import SessionHistory


def _history(tmp_path: Path, **kwargs: int) -> SessionHistory:
    return SessionHistory(tmp_path / "book-hash" / "tui_history", **kwargs)


def test_previous_walks_back_newest_first(tmp_path: Path) -> None:
    h = _history(tmp_path)
    h.add("first")
    h.add("second")
    assert h.previous() == "second"
    assert h.previous() == "first"
    assert h.previous() is None  # oldest reached


def test_next_walks_forward_to_live_prompt(tmp_path: Path) -> None:
    h = _history(tmp_path)
    h.add("first")
    h.add("second")
    h.previous()
    h.previous()
    assert h.next() == "second"
    assert h.next() == ""  # back at the live (empty) prompt
    assert h.next() is None  # nothing past it


def test_persists_across_instances(tmp_path: Path) -> None:
    _history(tmp_path).add("redux state")
    reopened = _history(tmp_path)
    assert reopened.previous() == "redux state"


def test_consecutive_duplicates_collapse(tmp_path: Path) -> None:
    h = _history(tmp_path)
    h.add("same")
    h.add("same")
    assert h.previous() == "same"
    assert h.previous() is None


def test_blank_entries_ignored(tmp_path: Path) -> None:
    h = _history(tmp_path)
    h.add("   ")
    assert h.previous() is None


def test_capped_at_limit(tmp_path: Path) -> None:
    h = _history(tmp_path, limit=3)
    for i in range(5):
        h.add(f"entry {i}")
    reopened = _history(tmp_path, limit=3)
    assert reopened.previous() == "entry 4"
    assert reopened.previous() == "entry 3"
    assert reopened.previous() == "entry 2"
    assert reopened.previous() is None


def test_add_resets_cursor(tmp_path: Path) -> None:
    h = _history(tmp_path)
    h.add("first")
    h.previous()
    h.add("second")
    assert h.previous() == "second"


def test_reset_returns_to_live_prompt(tmp_path: Path) -> None:
    h = _history(tmp_path)
    h.add("first")
    h.previous()
    h.reset()
    assert h.previous() == "first"


def test_missing_file_is_empty_history(tmp_path: Path) -> None:
    h = SessionHistory(tmp_path / "nowhere" / "tui_history")
    assert h.previous() is None
