#!/bin/bash
# WealthTrack launcher for Mac
cd "$(dirname "$0")"

PYTHON=python3
if ! command -v $PYTHON >/dev/null 2>&1; then
  echo "Python 3 is not installed. Install it from https://www.python.org/downloads/ and try again."
  read -p "Press Enter to close..."
  exit 1
fi

echo "Installing/checking dependencies (first run may take a minute)..."
$PYTHON -m pip install --user -r requirements.txt --quiet --disable-pip-version-check \
  || $PYTHON -m pip install --user --break-system-packages -r requirements.txt --quiet --disable-pip-version-check

echo "Starting WealthTrack server..."
( sleep 2 && open "http://127.0.0.1:8000" ) &
$PYTHON -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

read -p "Server stopped. Press Enter to close..."
