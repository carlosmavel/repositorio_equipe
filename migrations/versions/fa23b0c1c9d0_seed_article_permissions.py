"""seed article permissions

Revision ID: fa23b0c1c9d0
Revises: f5c6d7e8a9b0
Create Date: 2025-06-21 00:18:46.929087

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa23b0c1c9d0'
down_revision = 'f5c6d7e8a9b0'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    perms = [
        ("artigo_criar", "Criar artigo"),
        ("artigo_editar", "Editar artigo"),
        ("artigo_aprovar", "Aprovar artigo"),
        ("artigo_revisar", "Revisar artigo"),
        ("artigo_assumir_revisao", "Assumir revisão"),
    ]
    for codigo, nome in perms:
        res = connection.execute(
            sa.text("SELECT id FROM funcao WHERE codigo=:c"), {"c": codigo}
        ).first()
        if not res:
            connection.execute(
                sa.text(
                    "INSERT INTO funcao (codigo, nome) VALUES (:c, :n)"
                ),
                {"c": codigo, "n": nome},
            )


def downgrade():
    connection = op.get_bind()
    codes = [
        "artigo_criar",
        "artigo_editar",
        "artigo_aprovar",
        "artigo_revisar",
        "artigo_assumir_revisao",
    ]
    connection.execute(
        sa.text("DELETE FROM funcao WHERE codigo = ANY(:codes)"),
        {"codes": codes},
    )
