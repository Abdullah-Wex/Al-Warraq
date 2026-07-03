"""Al-Warraq exceptions."""


class AlWarraqError(Exception):
    """Base error for Al-Warraq."""


class InvalidEpubError(AlWarraqError):
    """EPUB file is invalid or corrupt."""
