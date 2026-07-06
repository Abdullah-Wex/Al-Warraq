"""Library view: browse a folder of EPUBs and search across all of them."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ..book import Book
from ..exceptions import AlWarraqError
from ..library import find_books
from ..search import SearchHit
from .app import SHARED_CSS, BookScreen


class LibraryScreen(Screen[None]):
    """Book picker + cross-book search over one folder of EPUBs.

    The option list shows either the books (default) or the merged search
    results for the last query; Escape returns from results to books.
    """

    BINDINGS: ClassVar = [
        Binding("escape", "back_to_books", "Books", show=False),
        Binding("up", "move_highlight(-1)", show=False),
        Binding("down", "move_highlight(1)", show=False),
    ]

    def __init__(self, directory: Path) -> None:
        super().__init__()
        self.directory = directory
        self.paths = find_books(directory)
        self._books: dict[Path, Book] = {}
        # (book, hit) behind each option while showing search results.
        self._hits: list[tuple[Book, SearchHit]] = []

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.directory} · {len(self.paths)} book(s)", id="header",
        )
        yield OptionList(
            *(Option(p.name, id=str(p)) for p in self.paths), id="books",
        )
        yield Input(
            placeholder="search all books, or pick one and press Enter",
            id="prompt",
        )

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        if self.paths:
            self.query_one(OptionList).highlighted = 0
        self._load_titles()

    # ------------------------------------------------------------- selection

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected,
    ) -> None:
        self._activate(event.option_index)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.query_one(Input).value = ""
            self._search_all(query)
            return
        highlighted = self.query_one(OptionList).highlighted
        if highlighted is not None:
            self._activate(highlighted)  # empty Enter opens the highlighted row

    def action_back_to_books(self) -> None:
        if self._hits:
            self._show_books()
        else:
            self.query_one(Input).value = ""

    def action_move_highlight(self, delta: int) -> None:
        options = self.query_one(OptionList)
        if options.highlighted is None or not options.option_count:
            return
        options.highlighted = max(
            0, min(options.option_count - 1, options.highlighted + delta),
        )

    def _activate(self, index: int) -> None:
        """Open whatever the row at ``index`` stands for (book or search hit)."""
        if self._hits:
            book, hit = self._hits[index]
            ref = hit.anchor or hit.file
            self.app.push_screen(BookScreen(book, initial_command=f"/content {ref}"))
            return
        option_id = self.query_one(OptionList).get_option_at_index(index).id
        if option_id is not None:
            self._open_book(Path(option_id))

    # ------------------------------------------------------------------ work

    @work(thread=True, exclusive=True)
    def _load_titles(self) -> None:
        """Open each book off the UI thread and reveal real titles."""
        for i, path in enumerate(self.paths):
            self._status(f"opening {i + 1}/{len(self.paths)}: {path.name}")
            book = self._book(path)
            if book is None:
                continue
            label = f"{book.doc_title} · EPUB {book.version} · {path.name}"
            self.app.call_from_thread(self._relabel, str(path), label)
        self._status("")

    @work(thread=True, exclusive=True)
    def _search_all(self, query: str) -> None:
        """Search every book (indexing on first use) and merge by score."""
        merged: list[tuple[Book, SearchHit]] = []
        for i, path in enumerate(self.paths):
            self._status(f"searching {i + 1}/{len(self.paths)}: {path.name}")
            book = self._book(path)
            if book is None:
                continue
            try:
                merged.extend((book, hit) for hit in book.search(query, limit=5))
            except AlWarraqError:
                continue
        merged.sort(key=lambda pair: pair[1].score, reverse=True)
        self._status("")
        self.app.call_from_thread(self._show_hits, query, merged[:20])

    # ---------------------------------------------------------------- helpers

    def _book(self, path: Path) -> Book | None:
        """Open (and remember) one book; unreadable books are skipped."""
        if path not in self._books:
            try:
                self._books[path] = Book.open(path)
            except (AlWarraqError, OSError):
                return None
        return self._books[path]

    def _show_hits(self, query: str, hits: list[tuple[Book, SearchHit]]) -> None:
        self._hits = hits
        options = self.query_one(OptionList)
        options.clear_options()
        if not hits:
            options.add_option(Option(f"No matches for {query!r}", disabled=True))
            return
        for book, hit in hits:
            crumb = " › ".join([book.doc_title, *hit.breadcrumb])  # noqa: RUF001
            options.add_option(Option(f"{hit.score:6.2f}  {crumb}"))
        options.highlighted = 0
        options.focus()

    def _show_books(self) -> None:
        self._hits = []
        options = self.query_one(OptionList)
        options.clear_options()
        for path in self.paths:
            book = self._books.get(path)
            label = (
                f"{book.doc_title} · EPUB {book.version} · {path.name}"
                if book else path.name
            )
            options.add_option(Option(label, id=str(path)))
        options.highlighted = 0

    def _open_book(self, path: Path) -> None:
        book = self._book(path)
        if book is None:
            self._status(f"cannot open {path.name}")
            return
        self.app.push_screen(BookScreen(book))

    def _relabel(self, option_id: str, label: str) -> None:
        options = self.query_one(OptionList)
        if self._hits:
            return  # user already switched to search results
        options.replace_option_prompt(option_id, label)

    def _status(self, message: str) -> None:
        """Update the header's progress suffix (called from worker threads)."""
        suffix = f" — {message}" if message else ""
        self.app.call_from_thread(
            self.query_one("#header", Static).update,
            f"{self.directory} · {len(self.paths)} book(s){suffix}",
        )


class LibraryApp(App[None]):
    """Folder session: al-warraq ~/books/."""

    CSS = SHARED_CSS

    BINDINGS: ClassVar = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    def __init__(self, directory: Path) -> None:
        super().__init__()
        self.directory = directory

    def get_default_screen(self) -> LibraryScreen:
        return LibraryScreen(self.directory)
