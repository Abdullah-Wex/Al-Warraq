"""Widgets for the interactive app."""

from __future__ import annotations

from textual.widgets import OptionList
from textual.widgets.option_list import Option

from .commands import match


class CommandPopup(OptionList):
    """Filter-as-you-type list of slash commands, shown above the input.

    The app shows it while the input holds a bare ``/prefix`` and hides it
    otherwise; ``completion`` is the highlighted command's name.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.display = False
        self.can_focus = False

    def show_filtered(self, prefix: str) -> None:
        """Show the commands matching ``prefix``; hide when nothing matches."""
        commands = match(prefix)
        if not commands:
            self.hide()
            return
        self.clear_options()
        self.add_options(
            Option(f"{cmd.usage:<24} {cmd.help}", id=cmd.name) for cmd in commands
        )
        self.highlighted = 0
        self.display = True

    def hide(self) -> None:
        self.display = False

    @property
    def completion(self) -> str | None:
        """Name of the highlighted command, or None when hidden/empty."""
        if not self.display or self.highlighted is None:
            return None
        option = self.get_option_at_index(self.highlighted)
        return option.id

    def move_highlight(self, delta: int) -> None:
        """Move the highlight up (-1) or down (+1), clamped to the list."""
        if self.highlighted is None or not self.option_count:
            return
        self.highlighted = max(
            0, min(self.option_count - 1, self.highlighted + delta),
        )
