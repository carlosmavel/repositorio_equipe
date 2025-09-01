"""seed scoped article permissions"""

from alembic import op
import sqlalchemy as sa

try:
    from core.enums import Permissao
except ImportError:  # pragma: no cover - fallback when PYTHONPATH isn't set
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    from core.enums import Permissao

revision = 'bb1d9e24176f'
down_revision = 'fa23b0c1c9d0'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    perms = [(p.value, p.value.replace('_', ' ').capitalize()) for p in Permissao]

    # Generate ids manually to support databases without implicit
    # autoincrement on integer primary keys (e.g. Oracle).
    next_id = connection.execute(
        sa.text("SELECT COALESCE(MAX(id), 0) FROM funcao")
    ).scalar()

    for codigo, nome in perms:
        res = connection.execute(
            sa.text("SELECT id FROM funcao WHERE codigo=:c"), {"c": codigo}
        ).first()
        if not res:
            next_id += 1
            connection.execute(
                sa.text("INSERT INTO funcao (id, codigo, nome) VALUES (:i, :c, :n)"),
                {"i": next_id, "c": codigo, "n": nome},
            )


def downgrade():
    connection = op.get_bind()
    codes = [p.value for p in Permissao]
    connection.execute(
        sa.text("DELETE FROM funcao WHERE codigo = ANY(:codes)"),
        {"codes": codes},
    )
