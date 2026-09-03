"""
main.py — WealthTrack FastAPI backend.

Wires storage.py (local JSON persistence) + market_data.py (Yahoo Finance
via yfinance) + calculations.py (pure math) into the REST API contract
described in TASKS.md, and serves the static frontend/ directory at "/".

Owned by Agent 4. Do not modify market_data.py or calculations.py.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import calculations, market_data, storage
from backend.models import (
    ErrorResponse,
    HoldingCreate,
    HoldingOut,
    HoldingUpdate,
    PortfolioSummary,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(title="WealthTrack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Price cache
#
# Yahoo Finance is hit through yfinance on every price lookup, which is slow
# and rate-limit-prone if the frontend polls GET /api/holdings frequently
# (e.g. every few seconds) or a portfolio holds the same symbol multiple
# times. We keep a tiny in-process dict cache keyed by symbol:
#   {symbol: {"data": <get_current_price(...) result>, "fetched_at": <monotonic time>}}
# A lookup younger than PRICE_CACHE_TTL_SECONDS is served straight from the
# cache; anything older (or missing) triggers a fresh market_data call and
# re-populates the cache. This is a simple lazy/pull-based refresh (refreshed
# on the next request past the TTL) rather than a separate polling thread —
# it's enough to smooth out rapid UI polling while still keeping prices
# reasonably fresh, without adding background-thread lifecycle complexity to
# a single-process dev server.
# ---------------------------------------------------------------------------
PRICE_CACHE_TTL_SECONDS = 45
_price_cache: dict[str, dict] = {}


def _get_cached_price(symbol: str) -> dict:
    """Return market_data.get_current_price(symbol), using a short-TTL cache."""
    symbol = (symbol or "").strip().upper()
    now = time.monotonic()
    cached = _price_cache.get(symbol)
    if cached is not None and (now - cached["fetched_at"]) < PRICE_CACHE_TTL_SECONDS:
        return cached["data"]

    try:
        data = market_data.get_current_price(symbol)
    except Exception as exc:
        # Defensive: market_data already wraps its own exceptions, but a
        # Yahoo Finance outage should never be able to crash this endpoint.
        data = {
            "symbol": symbol,
            "price": None,
            "currency": None,
            "last_updated": None,
            "error": f"Unexpected error fetching price for '{symbol}': {exc}",
        }

    _price_cache[symbol] = {"data": data, "fetched_at": now}
    return data


def _enrich_holding(holding: dict) -> dict:
    """Attach live price + computed financials to a stored holding dict."""
    price_result = _get_cached_price(holding["symbol"])
    current_price = price_result.get("price")
    invested_amount = calculations.calculate_invested_amount(
        holding["quantity"], holding["purchase_price"]
    )

    enriched = {
        **holding,
        "current_price": current_price,
        "currency": price_result.get("currency"),
        "invested_amount": invested_amount,
        "current_value": None,
        "profit_loss": None,
        "return_pct": None,
        "last_updated": price_result.get("last_updated"),
        "price_error": price_result.get("error"),
    }

    if current_price is not None:
        current_value = calculations.calculate_current_value(holding["quantity"], current_price)
        profit_loss = calculations.calculate_profit_loss(invested_amount, current_value)
        return_pct = calculations.calculate_return_percentage(invested_amount, profit_loss)
        enriched.update(
            current_value=current_value,
            profit_loss=profit_loss,
            return_pct=return_pct,
        )

    return enriched


# ---------------------------------------------------------------------------
# Exception handlers — never leak a raw stack trace to the client.
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": f"Internal server error: {exc}"})


# ---------------------------------------------------------------------------
# Holdings CRUD
# ---------------------------------------------------------------------------
@app.get("/api/holdings", response_model=list[HoldingOut])
def list_holdings():
    holdings = storage.get_all_holdings()
    return [_enrich_holding(h) for h in holdings]


@app.post("/api/holdings", response_model=HoldingOut, status_code=201)
def create_holding(payload: HoldingCreate):
    symbol = payload.symbol.strip().upper()

    try:
        is_valid = market_data.validate_symbol(symbol)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not validate symbol '{symbol}': {exc}"
        )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"'{symbol}' is not a valid/recognized stock symbol.",
        )

    holding = storage.add_holding(
        symbol=symbol,
        quantity=payload.quantity,
        purchase_price=payload.purchase_price,
        purchase_date=payload.purchase_date,
    )
    return _enrich_holding(holding)


@app.put("/api/holdings/{holding_id}", response_model=HoldingOut)
def edit_holding(holding_id: str, payload: HoldingUpdate):
    existing = storage.get_holding(holding_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No holding found with id '{holding_id}'.")

    new_symbol: Optional[str] = None
    if payload.symbol is not None:
        new_symbol = payload.symbol.strip().upper()
        try:
            is_valid = market_data.validate_symbol(new_symbol)
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"Could not validate symbol '{new_symbol}': {exc}"
            )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"'{new_symbol}' is not a valid/recognized stock symbol.",
            )

    updated = storage.update_holding(
        holding_id,
        symbol=new_symbol,
        quantity=payload.quantity,
        purchase_price=payload.purchase_price,
        purchase_date=payload.purchase_date,
    )
    return _enrich_holding(updated)


@app.delete("/api/holdings/{holding_id}")
def remove_holding(holding_id: str):
    deleted = storage.delete_holding(holding_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No holding found with id '{holding_id}'.")
    return {"deleted": True, "id": holding_id}


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------
@app.get("/api/portfolio/summary", response_model=PortfolioSummary)
def portfolio_summary():
    holdings = [_enrich_holding(h) for h in storage.get_all_holdings()]
    priced = [h for h in holdings if h["current_value"] is not None]

    totals = calculations.calculate_portfolio_totals(priced)

    return {
        **totals,
        "holdings_count": len(holdings),
        "priced_holdings_count": len(priced),
    }


# ---------------------------------------------------------------------------
# Historical prices
# ---------------------------------------------------------------------------
@app.get("/api/history/{symbol}")
def history(symbol: str, period: str = "1mo"):
    try:
        result = market_data.get_historical_prices(symbol, period=period)
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Could not fetch historical data for '{symbol}': {exc}"},
        )
    return result


# ---------------------------------------------------------------------------
# Static frontend — mounted last so it never shadows the /api/* routes above.
# `check_dir=False` lets the server start even if frontend/ is briefly empty
# before Agent 1's files land.
# ---------------------------------------------------------------------------
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True, check_dir=False), name="frontend")
