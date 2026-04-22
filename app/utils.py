"""Utility helpers for the CI/CD Practice App."""

from __future__ import annotations


def normalize_item_name(name: str) -> str:
    """Normalize user-provided item names into a stable display form."""
    compact = " ".join(name.split())
    return compact.title()
