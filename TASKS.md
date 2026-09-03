# WealthTrack — Shared Team Task List

Team: WealthTrack (5 agents). Stack: Python + FastAPI + yfinance (no API key), HTML/CSS/vanilla JS.
Project root: `/Users/arjunrajkumar/Desktop/Wealth/WealthTrack`

## Interface contracts (must not change without updating this file)

**`backend/market_data.py`** (Agent 2 owns)
- `get_current_price(symbol: str) -> dict`
  → `{"symbol": str, "price": float, "currency": str, "last_updated": ISO8601 str, "error": str|None}`
  On invalid/unknown symbol or network failure: `price=None`, `error="<human readable message>"`. Never fabricate a price.
- `get_historical_prices(symbol: str, period: str = "1mo") -> dict`
  → `{"symbol": str, "history": [{"date": "YYYY-MM-DD", "close": float}, ...], "error": str|None}`
- `validate_symbol(symbol: str) -> bool`

**`backend/calculations.py`** (Agent 3 owns)
- `calculate_invested_amount(quantity: float, purchase_price: float) -> float`
- `calculate_current_value(quantity: float, current_price: float) -> float`
- `calculate_profit_loss(invested_amount: float, current_value: float) -> float`
- `calculate_return_percentage(invested_amount: float, profit_loss: float) -> float`
- `calculate_portfolio_totals(holdings: list[dict]) -> dict` where each holding dict has
  `invested_amount`, `current_value`, `profit_loss` → returns
  `{"total_invested": float, "total_current_value": float, "total_profit_loss": float, "total_return_pct": float}`

**`backend/storage.py`** (Agent 4 owns) — local JSON file storage (`portfolio_data.json`), CRUD for holdings:
`{"id": str, "symbol": str, "quantity": float, "purchase_price": float, "purchase_date": str}`

**Backend API** (Agent 4 owns, `backend/main.py`, FastAPI, serves `frontend/` as static files too)
- `GET /api/holdings` — list holdings enriched with live price, invested amount, current value, P&L, return %, last_updated, and price error if any
- `POST /api/holdings` — add `{symbol, quantity, purchase_price, purchase_date?}`
- `PUT /api/holdings/{id}` — edit
- `DELETE /api/holdings/{id}` — remove
- `GET /api/portfolio/summary` — total invested, total current value, total P&L, total return %
- `GET /api/history/{symbol}?period=1mo` — historical prices for charts
- CORS enabled for local dev; graceful JSON error responses when Yahoo Finance is unreachable or symbol invalid (never 500 with a stack trace, never fake data)

**Frontend** (Agent 1 owns, `frontend/index.html`, `frontend/style.css`, `frontend/app.js`)
- Talks only to the API above (relative paths, e.g. `/api/holdings`)
- Table: symbol, quantity, purchase price, current price, invested, current value, P&L, return %, last updated
- Add/remove holding forms, portfolio summary cards, allocation + P&L charts (Chart.js via CDN), responsive layout, invalid-symbol error display

## Task list (check off as completed)

- [x] Agent 2 (Yahoo Finance): `backend/market_data.py` implementing contract above, using `yfinance`, no fake data, handles invalid symbols/network errors
  - No deviations from the contract's function signatures/return shapes.
  - One addition: `currency` is `None` (not a fabricated guess like `"USD"`) when Yahoo Finance doesn't report a currency for a symbol — the contract types it as `str` but this only happens on the already-documented failure path in practice; every successful lookup in testing (AAPL/MSFT/TSLA) returned a real currency string.
  - `yfinance` and `pandas` required in `requirements.txt` (installed locally via `pip install --user --break-system-packages yfinance pandas` due to Homebrew's externally-managed-environment restriction — Agent 4, no action needed beyond listing the two packages).
  - Self-test (`python3 backend/market_data.py`) confirmed real live prices: AAPL ~$329.07, MSFT ~$511.17, TSLA ~$381.71 (as of 2026-09-03), and correctly returned `price=None` with a clear error for `ZZZZINVALID`.
- [x] Agent 3 (Portfolio calculation): `backend/calculations.py` implementing contract above + a quick self-check of the math
  - no deviations from contract. Money values rounded to 2 decimals inside each function (invested/current/P&L/return%); `calculate_return_percentage` returns 0.0 when invested_amount is 0. `calculate_portfolio_totals` sums the three fields across holdings and derives `total_return_pct` from the summed totals (not an average of per-holding %). Self-test in `if __name__ == "__main__":` covers 3 holdings (a gain, a loss, and a fractional-quantity case) plus the zero-division guard and a hand-verified portfolio total; `python3 backend/calculations.py` run from project root — all assertions passed.
- [x] Agent 4 (Backend): `backend/storage.py`, `backend/models.py`, `backend/main.py` wiring storage + market_data + calculations into the API contract above; `requirements.txt`; auto price refresh
  - No deviations from the API/storage contract's endpoints, request/response shapes, or field names.
  - Additions (all additive, nothing removed/renamed from the contract): `HoldingOut` also includes `currency` (from market_data) and `return_pct`; `portfolio/summary` also includes `holdings_count` and `priced_holdings_count` alongside the four contracted total fields. Un-priced holdings (price fetch failed) are excluded from the summary totals but still counted in `holdings_count`.
  - Auto price refresh: implemented as an in-process per-symbol dict cache with a 45s TTL (lazy/pull-based — refreshed on the next request past the TTL, not a background polling thread), so rapid UI polling of `GET /api/holdings` doesn't hammer Yahoo Finance. See comment block above `_get_cached_price` in `backend/main.py`.
  - Error handling: `POST`/`PUT` reject invalid symbols with a clean `400 {"detail": "..."}` (via `market_data.validate_symbol`, never a fabricated price); a Yahoo Finance-side failure on price/history lookups returns clean JSON errors (`price_error` field per-holding, or a `502 {"error": "..."}` for `/api/history/{symbol}`); a catch-all `Exception` handler ensures no endpoint can leak a raw stack trace (500 with clean JSON instead).
  - `requirements.txt` (project root) pins: fastapi==0.141.1, uvicorn==0.52.4, pydantic==2.13.5, yfinance==1.7.0, pandas==3.0.5, python-multipart==0.0.32 — installed via `python3 -m pip install --user --break-system-packages fastapi uvicorn pydantic python-multipart` (yfinance/pandas were already installed by Agent 2).
  - Static frontend mounted at `/` via `StaticFiles(..., html=True, check_dir=False)`, added **after** all `/api/*` routes so it never shadows them; `check_dir=False` + `frontend/` auto-created means the server starts cleanly even before Agent 1's files land (confirmed: `GET /` returns a clean `404 {"detail":"Not Found"}` right now, not a crash).
  - Live-tested end-to-end with real Yahoo Finance data: added AAPL (qty 10 @ $150) → live price $328.95, invested $1500, current value $3289.45, P&L +$1789.45, return +119.3%; `GET /api/portfolio/summary` matched; `POST` with symbol `ZZZZINVALID` → clean `400` (not a 500); `GET /api/history/AAPL?period=5d` → 5 rows of real closes; `DELETE` removed the test holding cleanly (holdings list empty again afterward, `portfolio_data.json` back to `[]`).
  - **Server is running now, in the background, for Agent 1 and Agent 5 to use:**
    - Start command (from project root): `PATH="$HOME/Library/Python/3.13/bin:$PATH" python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
    - Port: `8000` — API base `http://127.0.0.1:8000/api/...`, frontend served at `http://127.0.0.1:8000/`
    - cwd must be the project root (`/Users/arjunrajkumar/Desktop/Wealth/WealthTrack`) so `backend.main` imports and the `frontend/` relative mount resolve correctly.
- [x] Agent 1 (Frontend): `frontend/index.html`, `frontend/style.css`, `frontend/app.js` per contract above, responsive, charts
  - No deviations from the API contract — consumed the exact fields Agent 4 documented (`current_price`, `invested_amount`, `current_value`, `profit_loss`, `return_pct`, `last_updated`, `price_error`, plus summary's `holdings_count`/`priced_holdings_count`).
  - Charts: allocation doughnut (by `current_value` per holding) + a P&L bar chart per holding (green/red bars), both Chart.js via CDN (`https://cdn.jsdelivr.net/npm/chart.js`, no key needed). Chose the P&L bar over a historical price line chart to keep both charts driven by the already-polled `/api/holdings` response (no extra endpoint calls needed on every refresh); charts show an empty-state message when there are no priced holdings instead of rendering blank axes.
  - Table shows an edit-free remove-only row action (edit was the noted stretch goal; removal works via `DELETE /api/holdings/{id}` + refetch).
  - Add-holding form: POST with inline error display near the form on 400 (shows `detail` message, doesn't alert()/swallow it); form resets and dashboard refetches on success.
  - Auto-refresh: polls `GET /api/holdings` + `GET /api/portfolio/summary` every 45s (matches backend's 45s price cache TTL so polling never queries stale-vs-fresh unpredictably); per-holding "last updated" timestamp shown in the table so staleness is visible; background poll failures show a dismissible-on-next-success toast instead of blanking the UI, and unavailable per-holding prices (price_error) render as "unavailable" with the error as a tooltip rather than fake numbers.
  - Responsive: summary cards go 4→2→1 columns, add-form goes 4-col→2-col→1-col, table wrapper has `overflow-x:auto` so it scrolls horizontally on narrow screens instead of breaking layout, charts stack to one column under 860px.
  - Verification: confirmed `GET http://127.0.0.1:8000/` now serves `index.html` (200 `text/html`, was a 404 before these files landed), and `style.css`/`app.js` both serve 200 from the static mount. Added one real sample holding via curl (`AAPL`, qty 10 @ $150) so QA sees a populated dashboard on first load — live price ~$328.81, invested $1500, current value $3288.10, P&L +$1788.10, return +119.21%, matching what `/api/holdings` and `/api/portfolio/summary` returned; left it in place (did not delete) per the task's "your call" — QA can add more or remove it as needed. Also re-confirmed `POST` with an invalid symbol (`ZZZZINVALID`) still returns a clean `400 {"detail": "..."}`, which the form now surfaces inline. Checked `frontend/app.js` with `node --check` — no syntax errors.
- [x] Agent 5 (QA): add real holdings (AAPL, MSFT, TSLA), verify prices vs Yahoo Finance, hand-verify all calculations, test invalid symbols, log bugs below, confirm fixes
  - Backend was already running from Agent 4's session; reused it, no restart needed.
  - Added MSFT (qty 5 @ $300) and TSLA (qty 8 @ $250) via `POST /api/holdings` — both returned `201` with live `current_price` (MSFT $510.70, TSLA $381.72).
  - Price cross-check (yfinance `fast_info['last_price']` vs API, same moment): AAPL API $328.50 vs independent $328.55; MSFT API $510.70001220703125 vs independent $510.70001220703125 (exact match); TSLA API $381.721 vs independent $381.77. All differences are sub-$0.10, consistent with seconds-apart market ticks — no fabrication/staleness.
  - Manual calc verification (hand math, all matched API output exactly):
    - AAPL: invested=10×150=1500.00 ✓; current=10×328.50=3285.00 ✓; P&L=3285.00−1500.00=1785.00 ✓; return=1785/1500×100=119.00% ✓
    - MSFT: invested=5×300=1500.00 ✓; current=5×510.70001…=2553.50 ✓; P&L=2553.50−1500.00=1053.50 ✓; return=1053.50/1500×100=70.23% ✓
    - TSLA: invested=8×250=2000.00 ✓; current=8×381.72100…=3053.77 ✓; P&L=3053.77−2000.00=1053.77 ✓; return=1053.77/2000×100=52.69% ✓
    - Summary: total_invested=1500+1500+2000=5000.00 ✓; total_current=3285.00+2553.50+3053.77=8892.27 ✓; total_P&L=1785+1053.50+1053.77=3892.27 ✓; total_return=3892.27/5000×100=77.85% ✓ — all matched `GET /api/portfolio/summary` exactly.
  - Invalid symbol test: `ZZZZINVALID` and `NOTASTOCK123` both → clean `400 {"detail": "'<sym>' is not a valid/recognized stock symbol."}`, no 500, no fabricated price. Empty symbol → clean `422` pydantic validation error (min length). Lowercase `aapl` → accepted and normalized to `AAPL`, priced correctly (case-insensitive as expected).
  - PUT/DELETE test (on a throwaway holding): `PUT` changed qty 1→2 and purchase_price 100→120, recalculated invested/current/P&L/return correctly (240.00 / 657.20 / 417.20 / 173.83%, hand-verified). `DELETE` removed it; confirmed absent from subsequent `GET /api/holdings`.
  - Frontend smoke check: `GET /`, `/style.css`, `/app.js` all `200` with correct content-types. Read `frontend/app.js` in full — it calls only real `/api/*` endpoints (no mock/hardcoded data, confirmed via grep), and `showFormError` surfaces `POST` 400 errors inline near the add-holding form (not silent/alert).
  - **No bugs found.** Every endpoint, calculation, and edge case behaved exactly per contract on the first pass — no code changes were necessary.
  - Final state: `portfolio_data.json` left with exactly AAPL (10 @ $150), MSFT (5 @ $300), TSLA (8 @ $250) — the throwaway test holding was deleted. Backend confirmed still running (`GET /api/holdings` → 200) at the end of QA.

## Bugs found by QA (Agent 5 fills in)

**No bugs found.** All categories tested clean on the first pass:
- Real stock POSTs (AAPL/MSFT/TSLA): all 201 with live prices — no bug.
- Price cross-check vs independent yfinance call: prices matched within normal seconds-apart movement — no fabrication/staleness — no bug.
- Manual calculation verification (per-holding + portfolio summary): every value matched hand-calculated math exactly — no bug.
- Invalid symbols (`ZZZZINVALID`, `NOTASTOCK123`, empty string): clean 400/422 JSON errors, no 500s, no fake prices — no bug.
- Lowercase symbol (`aapl`): correctly normalized and priced — no bug.
- DELETE / PUT edit: both worked correctly with proper recalculation on edit — no bug.
- Frontend: static files all 200, `app.js` calls only real endpoints, invalid-symbol errors surface inline in the UI — no bug.

## QA sign-off (Agent 5)

WealthTrack is confirmed working end-to-end with **real Yahoo Finance data** (no mocked/fabricated prices anywhere in the stack), **correct calculations** (hand-verified against every holding and the portfolio summary), and **clean handling of invalid symbols** (4xx JSON errors, never a 500 or fake price). Dashboard at http://127.0.0.1:8000/ is populated with 3 real holdings (AAPL, MSFT, TSLA) and backend server is running. App is ready for the user.
