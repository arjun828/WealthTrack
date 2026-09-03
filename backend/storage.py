"""
storage.py — local JSON file storage for WealthTrack holdings.

Persists holdings as a flat JSON array at `<project_root>/portfolio_data.json`.
The file is created (as `[]`) on first use if it doesn't exist yet.

Each holding is a dict:
    {"id": str (uuid4), "symbol": str, "quantity": float,
     "purchase_price": float, "purchase_date": str}

Concurrency approach: this is a simple local single-process dev app (no
multi-worker uvicorn, no separate writer processes), so we don't need a
real database or file-locking library. Every operation does a full
read-modify-write of the JSON file, which is "concurrent-safe-enough"
for the sequential/low-concurrency requests FastAPI's single default
worker will actually serve — it just avoids keeping any in-memory state
that could drift from disk between requests.

Owned by Agent 4. See TASKS.md for the interface contract.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

# project_root/portfolio_data.json — this file lives at project_root/backend/storage.py
DATA_FILE = Path(__file__).resolve().parent.parent / "portfolio_data.json"


def _ensure_file() -> None:
    """Create the data file with an empty list if it doesn't exist yet."""
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list:
    """Read and return the full list of holdings from disk."""
    _ensure_file()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable file — fail safe to an empty portfolio
        # rather than crashing the API.
        return []


def _write_all(holdings: list) -> None:
    """Write the full list of holdings to disk."""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(holdings, f, indent=2)


def get_all_holdings() -> list:
    """Return all stored holdings."""
    return _read_all()


def get_holding(holding_id: str) -> dict | None:
    """Return a single holding by id, or None if not found."""
    for h in _read_all():
        if h["id"] == holding_id:
            return h
    return None


def add_holding(symbol: str, quantity: float, purchase_price: float, purchase_date: str) -> dict:
    """Create and persist a new holding. Returns the created holding dict."""
    holding = {
        "id": str(uuid.uuid4()),
        "symbol": symbol.strip().upper(),
        "quantity": float(quantity),
        "purchase_price": float(purchase_price),
        "purchase_date": purchase_date,
    }
    holdings = _read_all()
    holdings.append(holding)
    _write_all(holdings)
    return holding


def update_holding(holding_id: str, **fields) -> dict | None:
    """
    Update an existing holding with the given fields (symbol, quantity,
    purchase_price, purchase_date — any subset). Returns the updated
    holding dict, or None if no holding with that id exists.
    """
    holdings = _read_all()
    updated = None
    for h in holdings:
        if h["id"] == holding_id:
            if "symbol" in fields and fields["symbol"] is not None:
                h["symbol"] = fields["symbol"].strip().upper()
            if "quantity" in fields and fields["quantity"] is not None:
                h["quantity"] = float(fields["quantity"])
            if "purchase_price" in fields and fields["purchase_price"] is not None:
                h["purchase_price"] = float(fields["purchase_price"])
            if "purchase_date" in fields and fields["purchase_date"] is not None:
                h["purchase_date"] = fields["purchase_date"]
            updated = h
            break
    if updated is not None:
        _write_all(holdings)
    return updated


def delete_holding(holding_id: str) -> bool:
    """Delete a holding by id. Returns True if it was found and removed."""
    holdings = _read_all()
    remaining = [h for h in holdings if h["id"] != holding_id]
    if len(remaining) == len(holdings):
        return False
    _write_all(remaining)
    return True


if __name__ == "__main__":
    # Quick self-check.
    _ensure_file()
    before = get_all_holdings()
    h = add_holding("AAPL", 10, 150.0, "2026-01-01")
    assert get_holding(h["id"]) is not None
    updated = update_holding(h["id"], quantity=20)
    assert updated["quantity"] == 20.0
    assert delete_holding(h["id"]) is True
    assert get_holding(h["id"]) is None
    after = get_all_holdings()
    assert len(after) == len(before)
    print("storage.py self-test passed.")
