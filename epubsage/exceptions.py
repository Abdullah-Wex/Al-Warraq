"""epubsage exceptions."""


class EpubSageError(Exception):
    """Base error for epubsage."""


class InvalidEpubError(EpubSageError):
    """EPUB file is invalid or corrupt."""
