"""Add Comment table

Revision ID: 67ef260f5a21
Revises: 0001_initial
Create Date: 2025-05-22 17:07:52.415963
"""

from alembic import op
import sqlalchemy as sa

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
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )

    # 2) url em notification vira NOT NULL
    with op.batch_alter_table("notification") as batch_op:
        batch_op.alter_column(
            "url",
            existing_type=sa.VARCHAR(length=255),
            nullable=False,
        )

    # 3) created_at em revision_request deixa de ser NOT NULL
    with op.batch_alter_table("revision_request") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            existing_server_default=sa.text("CURRENT_TIMESTAMP"),
        )


def downgrade():
    # 1) Reverte alteração de revision_request
    with op.batch_alter_table("revision_request") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            existing_server_default=sa.text("CURRENT_TIMESTAMP"),
        )

    # 2) url em notification volta a aceitar NULL
    with op.batch_alter_table("notification") as batch_op:
        batch_op.alter_column(
            "url",
            existing_type=sa.VARCHAR(length=255),
            nullable=True,
        )

    # 3) Remove a tabela comment
    op.drop_table("comment")

