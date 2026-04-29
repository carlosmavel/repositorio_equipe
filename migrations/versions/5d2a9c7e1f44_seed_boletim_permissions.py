"""seed boletim permissions

Revision ID: 5d2a9c7e1f44
Revises: bb1d9e24176f
Create Date: 2026-04-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '5d2a9c7e1f44'
down_revision = 'bb1d9e24176f'
branch_labels = None
depends_on = None


PERMISSIONS = (
    ("boletim_visualizar", "Boletim visualizar"),
    ("boletim_buscar", "Boletim buscar"),
    ("boletim_gerenciar", "Boletim gerenciar"),
)


def upgrade():
    connection = op.get_bind()
    for codigo, nome in PERMISSIONS:
        exists = connection.execute(
            sa.text("SELECT 1 FROM funcao WHERE codigo = :codigo LIMIT 1"),
            {"codigo": codigo},
        ).first()
        if not exists:
            connection.execute(
                sa.text("INSERT INTO funcao (codigo, nome) VALUES (:codigo, :nome)"),
                {"codigo": codigo, "nome": nome},
            )


def downgrade():
    connection = op.get_bind()
    codes = [codigo for codigo, _ in PERMISSIONS]
    connection.execute(
        sa.text("DELETE FROM funcao WHERE codigo = ANY(:codes)"),
        {"codes": codes},
    )
