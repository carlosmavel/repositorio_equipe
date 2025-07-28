#!/usr/bin/env bash
set -e

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
flask db upgrade

# Seed initial data (optional but recommended)
python seed.py

echo "Setup complete."
