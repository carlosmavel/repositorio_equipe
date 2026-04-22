import os
import sys

# Garante que o diretório raiz do projeto esteja no PYTHONPATH quando executado diretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database import db  # pragma: no cover
except ImportError:
    from ..core.database import db
from app import app

try:
    from core.services.permission_sync import sync_permission_catalog
except ImportError:  # pragma: no cover - fallback para execução em pacote
    from ..core.services.permission_sync import sync_permission_catalog


def run():
    with app.app_context():
        result = sync_permission_catalog(db.session)
        db.session.commit()
        print(
            "Funções criadas/atualizadas. "
            f"created={result.created} updated={result.updated} unchanged={result.unchanged}"
        )


if __name__ == "__main__":
    run()
