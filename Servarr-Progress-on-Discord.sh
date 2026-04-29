#!/bin/bash
# Launcher for qBittorrent Discord Webhook Service (Linux/Mac)

echo ""
echo "================================================================"
echo "qBittorrent Discord Webhook Service"
echo "================================================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.10 or later"
    exit 1
fi

# Check if virtual environment exists
if [ ! -f ".venv/bin/python" ]; then
    echo "Virtual environment not found. Creating it now..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
    echo "Virtual environment created successfully!"
    echo ""
fi

# Check if requirements are installed by trying to import a key dependency
echo "Checking dependencies..."
.venv/bin/python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies from requirements.txt..."
    .venv/bin/pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
    echo "Dependencies installed successfully!"
    echo ""
fi

# Check if .env file exists
if [ -f ".env" ]; then
    echo "Configuration found. Starting service..."
    echo ""
    .venv/bin/python main.py
else
    echo "Configuration not found. Starting setup wizard..."
    echo ""
    .venv/bin/python setup.py
fi
