"""
models.py — Pydantic request/response models for the WealthTrack API.

Owned by Agent 4. See TASKS.md for the interface contract.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    """Request body for POST /api/holdings."""

    symbol: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    purchase_price: float = Field(..., gt=0)
    purchase_date: Optional[str] = None


class HoldingUpdate(BaseModel):
    """Request body for PUT /api/holdings/{id}. All fields optional (partial update)."""

    symbol: Optional[str] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    purchase_price: Optional[float] = Field(default=None, gt=0)
    purchase_date: Optional[str] = None


class HoldingOut(BaseModel):
    """Response shape for a single holding, enriched with live market data."""

    id: str
    symbol: str
    quantity: float
    purchase_price: float
    purchase_date: Optional[str] = None

    current_price: Optional[float] = None
    currency: Optional[str] = None
    invested_amount: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    return_pct: Optional[float] = None

    last_updated: Optional[str] = None
    price_error: Optional[str] = None


class PortfolioSummary(BaseModel):
    """Response shape for GET /api/portfolio/summary."""

    total_invested: float
    total_current_value: float
    total_profit_loss: float
    total_return_pct: float
    holdings_count: int
    priced_holdings_count: int


class ErrorResponse(BaseModel):
    """Generic clean error body — never a raw stack trace."""

    error: str
