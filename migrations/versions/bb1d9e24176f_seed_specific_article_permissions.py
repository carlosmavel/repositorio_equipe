"""seed scoped article permissions"""

from alembic import op
import sqlalchemy as sa

try:
    from enums import Permissao
except ImportError:  # pragma: no cover - fallback
    from ..enums import Permissao

revision = 'bb1d9e24176f'
down_revision = 'fa23b0c1c9d0'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    perms = [(p.value, p.value.replace('_', ' ').capitalize()) for p in Permissao]
    for codigo, nome in perms:
        res = connection.execute(
            sa.text("SELECT id FROM funcao WHERE codigo=:c"), {"c": codigo}
        ).first()
        if not res:
            connection.execute(
                sa.text("INSERT INTO funcao (codigo, nome) VALUES (:c, :n)"),
                {"c": codigo, "n": nome},
            )


def downgrade():
    connection = op.get_bind()
    codes = [p.value for p in Permissao]
    connection.execute(
        sa.text("DELETE FROM funcao WHERE codigo = ANY(:codes)"),
        {"codes": codes},
    )
