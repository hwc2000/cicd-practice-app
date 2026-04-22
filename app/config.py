"""Configuration helpers for runtime defaults."""

from __future__ import annotations

import os


def get_item_source() -> str:
    """Return the source label used in item responses."""
    return os.getenv("ITEM_SOURCE", "api")
