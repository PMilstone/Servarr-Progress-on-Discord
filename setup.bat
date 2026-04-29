@echo off
REM Setup wizard for qBittorrent Discord Webhook Service (Windows)

echo.
echo ================================================================
echo qBittorrent Discord Webhook Service - Setup Wizard
echo ================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10 or later from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Run setup script with virtual environment
.venv\Scripts\python.exe setup.py

pause
