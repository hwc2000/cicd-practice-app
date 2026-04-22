"""Business logic layer for the CI/CD Practice App."""

from __future__ import annotations

from typing import Any


def normalize_item_name(name: str) -> str:
    """Normalize item names by trimming spaces and title-casing words."""
    return " ".join(name.split()).title()


# In-memory store (simulates DB)
_items: dict[int, dict[str, Any]] = {}
_next_id: int = 1


def calculate_total_price(price: float, quantity: int, discount_percent: float) -> float:
    """Calculate the total price after applying discount.

    Formula: total = price * quantity * (1 - discount / 100)

    Example:
        price=100, quantity=2, discount=10 → 100 * 2 * 0.9 = 180.0
    """
    subtotal = price * quantity
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal - discount_amount
    return round(total, 2)


def build_item_record(
    item_id: int,
    name: str,
    price: float,
    quantity: int,
    discount_percent: float,
    total_price: float,
    source: str,
) -> dict[str, Any]:
    """Build the canonical item payload used by the API and in-memory store."""
    return {
        "id": item_id,
        "name": normalize_item_name(name),
        "price": price,
        "quantity": quantity,
        "discount_percent": discount_percent,
        "total": total_price,
    }


def create_item(name: str, price: float, quantity: int, discount_percent: float) -> dict[str, Any]:
    """Create a new item and return its data."""
    global _next_id
    total = calculate_total_price(price, quantity, discount_percent)
    item = build_item_record(
        item_id=_next_id,
        name=name,
        price=price,
        quantity=quantity,
        discount_percent=discount_percent,
        total_price=total,
    )
    _items[_next_id] = item
    _next_id += 1
    return item


def get_item(item_id: int) -> dict[str, Any] | None:
    """Retrieve an item by ID."""
    return _items.get(item_id)


def list_items(min_price: float | None = None) -> list[dict[str, Any]]:
    """List all items, optionally filtering by minimum price."""
    items = list(_items.values())
    if min_price is not None:
        items = [i for i in items if i["price"] >= min_price]
    return items


def reset_store() -> None:
    """Reset the in-memory store (for testing)."""
    global _next_id
    _items.clear()
    _next_id = 1
