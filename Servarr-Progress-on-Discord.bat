@echo off
REM Launcher for qBittorrent Discord Webhook Service (Windows)

echo.
echo ================================================================
echo qBittorrent Discord Webhook Service
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
    echo Virtual environment not found. Creating it now...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
    echo.
)

REM Check if requirements are installed by trying to import a key dependency
echo Checking dependencies...
.venv\Scripts\python.exe -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies from requirements.txt...
    .venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
    echo.
)

REM Check if .env file exists
if exist ".env" (
    echo Configuration found. Starting service...
    echo.
    .venv\Scripts\python.exe main.py
) else (
    echo Configuration not found. Starting setup wizard...
    echo.
    .venv\Scripts\python.exe setup.py
)

pause
