#!/usr/bin/env bash
set -e

# Create virtual environment if it doesn't exist
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Load environment variables from .env when available so DATABASE_URI/SECRET_KEY are accessible
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

# Install dependencies only if the network is reachable
if ping -c1 -W1 pypi.org >/dev/null 2>&1; then
    python -m pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "No network connection, skipping dependency installation"
fi

# Apply database migrations when DATABASE_URI is configured and points to PostgreSQL
if [ -n "$DATABASE_URI" ]; then
    if [[ "$DATABASE_URI" == postgresql* ]]; then
        flask db upgrade
    else
        echo "DATABASE_URI definido, mas não parece ser PostgreSQL. Migrações não foram executadas."
    fi
fi

# Seed initial data (optional but recommended)
python -m seeds.seed

echo "Setup complete."
