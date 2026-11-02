#!/usr/bin/env bash
# Academic Deadline Management Assistant - Launch Script

set -e

echo "=== Academic Deadline Management Assistant ==="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# Set up virtual environment if not present
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Verifying dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Check .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
    fi
fi

# Launch Streamlit Dashboard
echo "Launching Streamlit application..."
streamlit run app.py

