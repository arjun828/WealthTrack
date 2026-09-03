@echo off
REM WealthTrack launcher for Windows
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed or not on PATH.
    echo Install it from https://www.python.org/downloads/ and check "Add Python to PATH" during setup.
    pause
    exit /b 1
)

echo Installing/checking dependencies (first run may take a minute)...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check

echo Starting WealthTrack server...
start "" http://127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
