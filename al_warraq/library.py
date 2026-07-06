"""Discover EPUBs in a directory — the functional core of the library view.

A "book" is either a zipped ``.epub`` file or an unzipped EPUB package
directory (see :func:`al_warraq.epub.is_epub_package`). Cloud placeholder
stubs (e.g. ``.icloud`` files for not-yet-downloaded books) are skipped.
"""

from __future__ import annotations

from pathlib import Path

from .epub import is_epub_package


def find_books(directory: str | Path) -> list[Path]:
    """Every book directly inside ``directory``, sorted by name.

    Non-recursive by design: one folder of books is the unit the library
    view works with, and recursing into package directories would find
    their internal files.
    """
    base = Path(directory)
    books: list[Path] = []
    for entry in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.endswith(".icloud"):
            continue  # cloud placeholder — content not on disk
        if (entry.is_file() and entry.suffix == ".epub") or is_epub_package(entry):
            books.append(entry)
    return books
