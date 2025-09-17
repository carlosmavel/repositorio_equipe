"""CLI to validate Oracle database connectivity using SQLAlchemy.

Run with ``python -m tools.test_oracle``.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def main() -> int:
    """Attempt to connect to the database and confirm permissions.

    Reads the ``DATABASE_URL`` environment variable, establishes a connection
    via SQLAlchemy and tries to create and drop a temporary table. Any failure
    returns a non-zero exit status.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL environment variable not set", file=sys.stderr)
        return 1

    engine = create_engine(db_url)

    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE TEST_ORACLE_CONNECTION (id NUMBER)"))
            connection.execute(text("DROP TABLE TEST_ORACLE_CONNECTION"))
        print("Database connection and permissions verified")
        return 0
    except SQLAlchemyError as exc:  # pragma: no cover - error handling
        print(f"Database test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module execution
    raise SystemExit(main())
