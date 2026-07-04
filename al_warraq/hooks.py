"""Hook interfaces — where a host application plugs its own strategies in.

``process_epub()`` accepts these two hooks. Both are structural protocols:
any object with a matching method works, no inheritance required. The
library calls the hooks; hooks never call back into the host — strategy
injection is the only doorway.

Contract for implementers:
- ``PassageSplitter.split`` takes one chapter's plain text and returns the
  passage texts, in reading order. The pipeline assigns positions and
  offsets, so splitters stay trivial and output stays deterministic.
- ``Embedder.embed`` takes all passage texts of a book (one batched call)
  and returns one vector per passage, same order and length.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class PassageSplitter(Protocol):
    """Splits one chapter's text into retrievable passages."""

    def split(self, chapter_text: str) -> Sequence[str]:
        """Return the chapter's passages, in reading order."""
        ...


@runtime_checkable
class Embedder(Protocol):
    """Turns passage texts into vectors."""

    def embed(self, passages: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one vector per passage, in the same order."""
        ...


@dataclass(frozen=True)
class StructuralSplitter:
    """Default PassageSplitter: group whole paragraphs up to a size budget.

    Splits on blank lines, then greedily packs consecutive paragraphs into
    passages of at most ``max_chars`` characters. A paragraph is never split,
    even when it alone exceeds the budget, and non-empty text always yields
    at least one passage.
    """

    max_chars: int = 2000

    def split(self, chapter_text: str) -> list[str]:
        paragraphs = [p.strip() for p in chapter_text.split("\n\n") if p.strip()]
        passages: list[str] = []
        current: list[str] = []
        current_len = 0

        for paragraph in paragraphs:
            grown = current_len + len(paragraph) + (2 if current else 0)
            if current and grown > self.max_chars:
                passages.append("\n\n".join(current))
                current, current_len = [], 0
            current.append(paragraph)
            current_len += len(paragraph) + (2 if current_len else 0)

        if current:
            passages.append("\n\n".join(current))
        return passages
