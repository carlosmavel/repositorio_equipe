"""seed artigo_excluir_definitivo and associate to admin global

Revision ID: 9f7a1b2c3d4e
Revises: fb34c1d2e3a4
Create Date: 2026-04-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '9f7a1b2c3d4e'
down_revision = 'fb34c1d2e3a4'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    codigo = "artigo_excluir_definitivo"
    nome = "Artigo excluir definitivo"

    permissao_id = connection.execute(
        sa.text("SELECT id FROM funcao WHERE codigo = :codigo"),
        {"codigo": codigo},
    ).scalar()

    if permissao_id is None:
        permissao_id = connection.execute(
            sa.text("INSERT INTO funcao (codigo, nome) VALUES (:codigo, :nome) RETURNING id"),
            {"codigo": codigo, "nome": nome},
        ).scalar_one()

    admin_id = connection.execute(
        sa.text("SELECT id FROM funcao WHERE codigo = 'admin'"),
    ).scalar()

    if admin_id is not None:
        assoc_exists = connection.execute(
            sa.text(
                """
                SELECT 1
                FROM user_funcoes
                WHERE user_id IN (
                    SELECT user_id FROM user_funcoes WHERE funcao_id = :admin_id
                )
                AND funcao_id = :permissao_id
                LIMIT 1
                """
            ),
            {"admin_id": admin_id, "permissao_id": permissao_id},
        ).first()

        if not assoc_exists:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO user_funcoes (user_id, funcao_id)
                    SELECT uf.user_id, :permissao_id
                    FROM user_funcoes uf
                    WHERE uf.funcao_id = :admin_id
                    AND NOT EXISTS (
                        SELECT 1 FROM user_funcoes existing
                        WHERE existing.user_id = uf.user_id
                        AND existing.funcao_id = :permissao_id
                    )
                    """
                ),
                {"admin_id": admin_id, "permissao_id": permissao_id},
            )


def downgrade():
    connection = op.get_bind()
    codigo = "artigo_excluir_definitivo"
    permissao_id = connection.execute(
        sa.text("SELECT id FROM funcao WHERE codigo = :codigo"),
        {"codigo": codigo},
    ).scalar()

    if permissao_id is None:
        return

    connection.execute(
        sa.text("DELETE FROM user_funcoes WHERE funcao_id = :permissao_id"),
        {"permissao_id": permissao_id},
    )
    connection.execute(
        sa.text("DELETE FROM funcao WHERE id = :permissao_id"),
        {"permissao_id": permissao_id},
    )
