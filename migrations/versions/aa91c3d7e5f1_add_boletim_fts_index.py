"""add boletim fts index

Revision ID: aa91c3d7e5f1
Revises: c7a1d9e6b2f4
Create Date: 2026-04-29 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'aa91c3d7e5f1'
down_revision = 'c7a1d9e6b2f4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_boletim_tsv_titulo_ocr
            ON boletim
            USING GIN (
                to_tsvector(
                    'portuguese',
                    coalesce(titulo, '') || ' ' || coalesce(ocr_text, '')
                )
            )
            """
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP INDEX IF EXISTS ix_boletim_tsv_titulo_ocr")
