"""
market_data.py — Yahoo Finance market data access for WealthTrack.

Provides live current price, historical price series, and symbol
validation via the `yfinance` library. This module never fabricates
data: on any failure (invalid/unknown symbol, network error, no data
returned by Yahoo Finance) it returns price=None / history=[] along
with a human-readable `error` string, and `validate_symbol` returns
False. All yfinance calls are wrapped in try/except so exceptions
never propagate out of this module.
"""

from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf


def _now_iso() -> str:
    """Current UTC timestamp as an ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def get_current_price(symbol: str) -> dict:
    """
    Fetch the latest known price for `symbol` from Yahoo Finance.

    Returns:
        {"symbol": str, "price": float|None, "currency": str|None,
         "last_updated": ISO8601 str, "error": str|None}

    On invalid symbol or network failure, price is None and error is
    a human-readable message. Never fabricates a price.
    """
    symbol = (symbol or "").strip().upper()
    last_updated = _now_iso()

    if not symbol:
        return {
            "symbol": symbol,
            "price": None,
            "currency": None,
            "last_updated": last_updated,
            "error": "Symbol is empty.",
        }

    try:
        ticker = yf.Ticker(symbol)
        price = None
        currency = None

        # 1) fast_info — cheap, doesn't scrape the full info page.
        try:
            fast_info = ticker.fast_info
            price = fast_info.get("lastPrice") if hasattr(fast_info, "get") else None
            if price is None:
                price = getattr(fast_info, "last_price", None)
            currency = fast_info.get("currency") if hasattr(fast_info, "get") else None
            if currency is None:
                currency = getattr(fast_info, "currency", None)
        except Exception:
            price = None
            currency = None

        # 2) .info — heavier, used only if fast_info didn't yield a price.
        if price is None:
            try:
                info = ticker.info or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                currency = currency or info.get("currency")
            except Exception:
                pass

        # 3) Fallback: most recent close from 1-day history.
        if price is None:
            try:
                hist = ticker.history(period="1d")
                if hist is not None and not hist.empty:
                    price = float(hist["Close"].iloc[-1])
            except Exception:
                pass

        if price is None:
            return {
                "symbol": symbol,
                "price": None,
                "currency": None,
                "last_updated": last_updated,
                "error": (
                    f"Could not retrieve a price for '{symbol}'. "
                    "It may be an invalid symbol or Yahoo Finance is unreachable."
                ),
            }

        return {
            "symbol": symbol,
            "price": float(price),
            "currency": currency,  # left as None if Yahoo Finance didn't report one — never guessed
            "last_updated": last_updated,
            "error": None,
        }

    except Exception as exc:
        return {
            "symbol": symbol,
            "price": None,
            "currency": None,
            "last_updated": last_updated,
            "error": f"Failed to fetch price for '{symbol}': {exc}",
        }


def get_historical_prices(symbol: str, period: str = "1mo") -> dict:
    """
    Fetch historical daily closing prices for `symbol` over `period`
    (any period string accepted by yfinance, e.g. "1d", "5d", "1mo",
    "6mo", "1y", "5y", "max").

    Returns:
        {"symbol": str, "history": [{"date": "YYYY-MM-DD", "close": float}, ...], "error": str|None}
    """
    symbol = (symbol or "").strip().upper()

    if not symbol:
        return {"symbol": symbol, "history": [], "error": "Symbol is empty."}

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist is None or hist.empty:
            return {
                "symbol": symbol,
                "history": [],
                "error": (
                    f"No historical data found for '{symbol}' (period={period}). "
                    "It may be an invalid symbol or Yahoo Finance is unreachable."
                ),
            }

        history = [
            {"date": index.strftime("%Y-%m-%d"), "close": float(row["Close"])}
            for index, row in hist.iterrows()
            if row["Close"] == row["Close"]  # drop NaN closes
        ]

        return {"symbol": symbol, "history": history, "error": None}

    except Exception as exc:
        return {
            "symbol": symbol,
            "history": [],
            "error": f"Failed to fetch historical data for '{symbol}': {exc}",
        }


def validate_symbol(symbol: str) -> bool:
    """
    Return True if `symbol` has a retrievable live price on Yahoo
    Finance, False otherwise (invalid symbol, empty input, or network
    failure — a False here means "could not confirm as valid", never
    a guess).
    """
    return get_current_price(symbol)["price"] is not None


if __name__ == "__main__":
    import json

    test_symbols = ["AAPL", "MSFT", "TSLA", "ZZZZINVALID"]

    for test_symbol in test_symbols:
        print(f"--- {test_symbol} ---")

        price_result = get_current_price(test_symbol)
        print("get_current_price:")
        print(json.dumps(price_result, indent=2))

        print("validate_symbol:", validate_symbol(test_symbol))

        if test_symbol != "ZZZZINVALID":
            hist_result = get_historical_prices(test_symbol, period="5d")
            print(f"get_historical_prices (5d): {len(hist_result['history'])} rows, error={hist_result['error']}")
            if hist_result["history"]:
                print("  latest:", hist_result["history"][-1])

        print()
