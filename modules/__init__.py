"""Utility modules for Kannada text processing."""

__all__ = ["pdf_to_word", "ocr_to_word", "legacy_kannada"]

from importlib import import_module


def __getattr__(name: str):
    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
