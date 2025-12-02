"""Application configuration for PostgreSQL-backed deployments."""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    """Carrega pares chave=valor de um arquivo .env para o ambiente."""

    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned_value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned_value)


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_env_file(ENV_PATH)


class Config:
    """Default configuration using PostgreSQL as the database backend."""

    SECRET_KEY = os.getenv("SECRET_KEY")
    PASSWORD_RESET_SECRET = os.getenv("PASSWORD_RESET_SECRET") or (
        f"{SECRET_KEY}_password_resets" if os.getenv("SECRET_KEY") else None
    )
    DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cookies de sessão endurecidos para evitar vazamentos em produção.
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

    if not SECRET_KEY or SECRET_KEY == "replace_with_your_secret_key":
        raise ValueError(
            "SECRET_KEY precisa ser definido no ambiente e não pode usar o valor padrão inseguro."
        )

    if not PASSWORD_RESET_SECRET:
        raise ValueError(
            "PASSWORD_RESET_SECRET precisa ser definido para geração de tokens de senha."
        )

    if not DATABASE_URI:
        raise ValueError("DATABASE_URI precisa ser definido no ambiente para uso do PostgreSQL.")

    allowed_schemes = ("postgresql", "postgresql+psycopg2")
    if not DATABASE_URI.startswith(allowed_schemes):
        if os.environ.get("ALLOW_SQLITE_FOR_TESTS") == "1" and DATABASE_URI.startswith("sqlite"):
            # Permite uso de banco em memória durante os testes automatizados.
            pass
        else:
            raise ValueError(
                "DATABASE_URI deve utilizar o esquema postgresql ou postgresql+psycopg2 para este projeto."
            )

    SQLALCHEMY_DATABASE_URI = DATABASE_URI

    # Evita conexões zumbis ao trabalhar com Docker/WSL
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
