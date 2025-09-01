import os

from tools import test_oracle


def test_test_oracle_cli_success(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert test_oracle.main() == 0
