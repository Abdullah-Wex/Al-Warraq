"""Input history for the interactive app, persisted per book.

One plain-text file per book (one line per input) under the book's cache
directory, so history survives across sessions but never leaves the machine.
No textual imports — plain-unit-testable.
"""

from __future__ import annotations

from pathlib import Path


class SessionHistory:
    """Recall previous inputs, newest first, like a shell prompt.

    The cursor starts past the end ("live" prompt). ``previous()`` walks
    back in time, ``next()`` walks forward again; ``add()`` appends and
    returns the cursor to the live prompt.
    """

    def __init__(self, path: Path, limit: int = 500) -> None:
        self.path = path
        self.limit = limit
        self._entries: list[str] = self._load()
        self._cursor = len(self._entries)

    def add(self, entry: str) -> None:
        """Record one submitted input; consecutive duplicates collapse."""
        entry = entry.strip()
        if entry and (not self._entries or self._entries[-1] != entry):
            self._entries.append(entry)
            self._entries = self._entries[-self.limit:]
            self._save()
        self._cursor = len(self._entries)

    def previous(self) -> str | None:
        """The entry one step back in time, or None at the oldest."""
        if self._cursor == 0:
            return None
        self._cursor -= 1
        return self._entries[self._cursor]

    def next(self) -> str | None:
        """The entry one step forward, '' back at the live prompt, None past it."""
        if self._cursor >= len(self._entries):
            return None
        self._cursor += 1
        if self._cursor == len(self._entries):
            return ""
        return self._entries[self._cursor]

    def reset(self) -> None:
        """Return the cursor to the live prompt (called when the user types)."""
        self._cursor = len(self._entries)

    def _load(self) -> list[str]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        return [line for line in lines if line.strip()][-self.limit:]

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("\n".join(self._entries) + "\n", encoding="utf-8")
        except OSError:
            pass  # history is a convenience — never break the app over it
