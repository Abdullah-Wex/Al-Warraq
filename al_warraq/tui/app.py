"""The interactive terminal app: al-warraq book.epub."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from rich.console import RenderableType
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, RichLog, Static

from ..book import Book
from .commands import execute
from .history import SessionHistory
from .widgets import CommandPopup


class WarraqApp(App[None]):
    """Header · scrollable results pane · bottom input with slash commands."""

    CSS = """
    #header {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    #prompt { dock: bottom; }
    #popup {
        dock: bottom;
        max-height: 9;
        border: round $primary;
    }
    #results { padding: 0 1; }
    """

    BINDINGS: ClassVar = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("escape", "dismiss_popup", "Clear", show=False),
        Binding("tab", "complete", "Complete", priority=True, show=False),
        Binding("up", "highlight(-1)", show=False),
        Binding("down", "highlight(1)", show=False),
        Binding("pageup", "scroll_results('up')", show=False),
        Binding("pagedown", "scroll_results('down')", show=False),
    ]

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.book = book
        self.history = SessionHistory(
            Path(book.output_dir) / book.hash / "tui_history",
        )
        self._recalling = False

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.book.doc_title} · EPUB {self.book.version} "
            f"· {self.book.toc_type}",
            id="header",
        )
        yield RichLog(wrap=True, markup=False, highlight=False, id="results")
        yield Input(placeholder="search, or / for commands", id="prompt")
        yield CommandPopup(id="popup")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self._write(Text("Type to search, / for commands, /help for the list."))

    # ------------------------------------------------------------------ input

    def on_input_changed(self, event: Input.Changed) -> None:
        popup = self.query_one(CommandPopup)
        if self._recalling:
            # A history recall isn't typing: keep walking history, no popup.
            self._recalling = False
            popup.hide()
            return
        self.history.reset()  # typing returns the cursor to the live prompt
        value = event.value
        if value.startswith("/") and " " not in value:
            popup.show_filtered(value)
        else:
            popup.hide()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        popup = self.query_one(CommandPopup)
        if popup.completion is not None and popup.completion != event.value:
            self._complete(popup.completion)
            return
        popup.hide()
        line = event.value.strip()
        if not line:
            return
        self.history.add(line)
        self.query_one(Input).value = ""
        self._write(Text(f"❯ {line}", style="bold"))  # noqa: RUF001
        self._run_command(line)

    # ----------------------------------------------------------------- actions

    def action_dismiss_popup(self) -> None:
        self.query_one(CommandPopup).hide()
        self.query_one(Input).value = ""

    def action_complete(self) -> None:
        completion = self.query_one(CommandPopup).completion
        if completion is not None:
            self._complete(completion)

    def action_highlight(self, delta: int) -> None:
        """Up/Down: popup highlight when visible, history recall otherwise."""
        popup = self.query_one(CommandPopup)
        if popup.display:
            popup.move_highlight(delta)
            return
        recalled = self.history.previous() if delta < 0 else self.history.next()
        if recalled is None:
            return
        self._recalling = True
        prompt = self.query_one(Input)
        prompt.value = recalled
        prompt.cursor_position = len(recalled)

    def action_scroll_results(self, direction: str) -> None:
        log = self.query_one(RichLog)
        if direction == "up":
            log.scroll_page_up()
        else:
            log.scroll_page_down()

    # ------------------------------------------------------------------- work

    @work(thread=True, exclusive=True)
    def _run_command(self, line: str) -> None:
        """Execute off the UI thread: first search builds the BM25 index."""
        result = execute(self.book, line)
        if result is None:
            self.call_from_thread(self.exit)
            return
        self.call_from_thread(self._write, result)

    # ---------------------------------------------------------------- helpers

    def _complete(self, name: str) -> None:
        """Put the highlighted command into the input, ready for arguments."""
        prompt = self.query_one(Input)
        prompt.value = f"{name} "
        prompt.cursor_position = len(prompt.value)
        self.query_one(CommandPopup).hide()

    def _write(self, renderable: RenderableType) -> None:
        log = self.query_one(RichLog)
        log.write(renderable, expand=True)
        log.write("")
