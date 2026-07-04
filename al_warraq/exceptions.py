"""Al-Warraq exceptions."""


class AlWarraqError(Exception):
    """Base error for Al-Warraq."""


class InvalidEpubError(AlWarraqError):
    """EPUB file is invalid or corrupt."""


class TocNotFoundError(AlWarraqError):
    """The EPUB has no usable table of contents (no NCX and no NAV)."""


class SectionNotFoundError(AlWarraqError):
    """The requested anchor or file has no matching TOC entry."""
