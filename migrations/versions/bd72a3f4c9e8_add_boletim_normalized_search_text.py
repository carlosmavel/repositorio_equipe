"""add boletim normalized search text

Revision ID: bd72a3f4c9e8
Revises: 4e6f8a1b2c3d
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'bd72a3f4c9e8'
down_revision = '4e6f8a1b2c3d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('boletim') as batch_op:
        batch_op.add_column(sa.Column('search_text_normalized', sa.Text(), nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            """
            UPDATE boletim
            SET search_text_normalized = lower(
                unaccent(regexp_replace(coalesce(titulo, '') || ' ' || coalesce(ocr_text, ''), '\\s+', ' ', 'g'))
            )
            WHERE search_text_normalized IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_boletim_search_text_normalized_trgm
            ON boletim USING GIN (search_text_normalized gin_trgm_ops)
            """
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP INDEX IF EXISTS ix_boletim_search_text_normalized_trgm")

    with op.batch_alter_table('boletim') as batch_op:
        batch_op.drop_column('search_text_normalized')
