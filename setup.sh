#!/bin/bash
# Setup wizard for qBittorrent Discord Webhook Service (Linux/Mac)

echo ""
echo "================================================================"
echo "qBittorrent Discord Webhook Service - Setup Wizard"
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
    echo "Error: Virtual environment not found"
    echo "Please run: python3 -m venv .venv"
    echo "Then run: .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Run setup script with virtual environment
.venv/bin/python setup.py
