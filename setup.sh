#!/usr/bin/env bash
set -e

# Create virtual environment if it doesn't exist
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies only if the network is reachable
if ping -c1 -W1 pypi.org >/dev/null 2>&1; then
    python -m pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "No network connection, skipping dependency installation"
fi

# Apply database migrations when DATABASE_URI is configured
if [ -n "$DATABASE_URI" ]; then
    flask db upgrade
fi

# Seed initial data (optional but recommended)
python seed.py

echo "Setup complete."
