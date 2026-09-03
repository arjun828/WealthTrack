# WealthTrack

A simple wealth portfolio tracker. Add stocks, quantities, and purchase prices — it pulls real, live
market prices from Yahoo Finance (via the free `yfinance` Python package, no API key needed) and shows
your invested amount, current value, profit/loss, and return %.

## Requirements

- Python 3.9+ installed and on your PATH (get it from https://www.python.org/downloads/ — on the
  installer, check "Add Python to PATH" on Windows).

## Run it

### Mac / Linux
1. Open the `WealthTrack` folder in Terminal.
2. Double-click `run_mac.command` (or run `./run_mac.command` in Terminal).
   - First run installs dependencies automatically; this can take a minute.
3. Your browser should open to http://127.0.0.1:8000 automatically. If not, open it manually.
4. To stop the server, close the Terminal window or press Ctrl+C in it.

### Windows
1. Open the `WealthTrack` folder in File Explorer.
2. Double-click `run_windows.bat`.
   - First run installs dependencies automatically; this can take a minute.
3. Your browser should open to http://127.0.0.1:8000 automatically. If not, open it manually.
4. To stop the server, close the command prompt window that opened.

## What it does

- Add a holding (stock symbol, quantity, purchase price) — the app validates the symbol against Yahoo
  Finance and rejects invalid ones with a clear error.
- Live current prices refresh automatically (~every 30-60s) — never fabricated; if Yahoo Finance is
  unreachable for a symbol you'll see a clear "unavailable" indicator instead of a fake price.
- Dashboard shows: invested amount, current value, profit/loss, return %, plus totals across your whole
  portfolio, with allocation and P&L charts.
- Data is stored locally in `portfolio_data.json` next to the app — nothing is sent anywhere except
  read-only price lookups to Yahoo Finance.

## Manual start (any OS, if you prefer the command line)

```
pip install -r requirements.txt
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 in your browser.

## Project structure

```
backend/
  main.py          FastAPI app + API routes
  storage.py        local JSON storage (portfolio_data.json)
  market_data.py     Yahoo Finance price lookups (yfinance)
  calculations.py    portfolio math (invested/current/P&L/return %)
  models.py          request/response models
frontend/
  index.html / style.css / app.js   the dashboard UI
requirements.txt
```
