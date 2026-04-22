"""Pydantic models for the CI/CD Practice App."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """Request body for creating an item."""
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    quantity: int = Field(default=1, ge=1)
    discount_percent: float = Field(default=0, ge=0, le=100)


class ItemResponse(BaseModel):
    """Response body for an item."""
    id: int
    name: str
    price: float
    quantity: int
    discount_percent: float
    total_price: float
    source: str
