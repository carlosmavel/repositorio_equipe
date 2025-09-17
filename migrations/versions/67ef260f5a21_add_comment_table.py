"""Add Comment table

Revision ID: 67ef260f5a21
Revises: 0001_initial
Create Date: 2025-05-22 17:07:52.415963
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "67ef260f5a21"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # 1) nova tabela de comentários
    op.create_table(
        "comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("artigo_id", sa.Integer(), sa.ForeignKey("article.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    # 2) Corrige o tipo ENUM article_status para usar rótulos minúsculos
    op.execute(
        """
        -- 2.1  Renomeia o enum atual (maiúsculo) para não colidir
        ALTER TYPE article_status RENAME TO article_status_old;

        -- 2.2  Cria o enum correto (minúsculo)
        CREATE TYPE article_status AS ENUM
          ('rascunho','pendente','em_revisao','em_ajuste','aprovado','rejeitado');

        -- 2.3  Converte a coluna, normalizando valores para minúsculo
        ALTER TABLE article
          ALTER COLUMN status DROP DEFAULT,
          ALTER COLUMN status TYPE article_status
            USING lower(status)::article_status,
          ALTER COLUMN status SET DEFAULT 'rascunho'::article_status;

        -- 2.4  Remove o enum antigo
        DROP TYPE article_status_old;
        """
    )


    # 3) url em notification vira NOT NULL
    with op.batch_alter_table("notification") as batch_op:
        batch_op.alter_column(
            "url",
            existing_type=sa.VARCHAR(length=255),
            nullable=False,
        )

    # 4) created_at em revision_request deixa de ser NOT NULL
    with op.batch_alter_table("revision_request") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            existing_server_default=sa.text("now()"),
        )


def downgrade():
    # 1) Reverte alteração de revision_request
    with op.batch_alter_table("revision_request") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            existing_server_default=sa.text("now()"),
        )

    # 2) url em notification volta a aceitar NULL
    with op.batch_alter_table("notification") as batch_op:
        batch_op.alter_column(
            "url",
            existing_type=sa.VARCHAR(length=255),
            nullable=True,
        )

    # 3) Converte enum → varchar
    op.execute(
        """
        ALTER TABLE article
          ALTER COLUMN status DROP DEFAULT,
          ALTER COLUMN status TYPE varchar(10) USING status::varchar,
          ALTER COLUMN status SET DEFAULT 'rascunho';
        """
    )

    # 4) Remove a tabela comment
    op.drop_table("comment")