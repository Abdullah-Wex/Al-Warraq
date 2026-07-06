"""Interactive terminal app — installed via the ``tui`` extra.

Nothing outside this package imports textual: the CLI checks for the extra
and only then calls :func:`run_app`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ..book import Book


def run_app(book: Book) -> None:
    """Open the interactive browser on an already-opened Book."""
    from .app import WarraqApp

    WarraqApp(book).run()


def run_library_app(directory: Path) -> None:
    """Open the library view over a folder of books."""
    from .library import LibraryApp

    LibraryApp(directory).run()
