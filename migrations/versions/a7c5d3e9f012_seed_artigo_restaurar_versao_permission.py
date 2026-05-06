"""seed artigo restaurar versao permission

Revision ID: a7c5d3e9f012
Revises: 6d8e9f0a1b2c
Create Date: 2026-05-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'a7c5d3e9f012'
down_revision = '6d8e9f0a1b2c'
branch_labels = None
depends_on = None


CODIGO = "artigo_restaurar_versao"
NOME = "Restaurar versão de artigo"


def upgrade():
    connection = op.get_bind()
    res = connection.execute(
        sa.text("SELECT id FROM funcao WHERE codigo = :codigo"),
        {"codigo": CODIGO},
    ).first()
    if not res:
        connection.execute(
            sa.text(
                """
                INSERT INTO funcao (codigo, nome, managed_by_system)
                VALUES (:codigo, :nome, true)
                """
            ),
            {"codigo": CODIGO, "nome": NOME},
        )


def downgrade():
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM funcao WHERE codigo = :codigo"),
        {"codigo": CODIGO},
    )
