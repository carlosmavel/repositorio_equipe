"""add fts indexes for article text and attachment ocr text

Revision ID: fb34c1d2e3a4
Revises: fa23b0c1c9d0
Create Date: 2026-04-24 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'fb34c1d2e3a4'
down_revision = 'fa23b0c1c9d0'
branch_labels = None
depends_on = None


def _is_postgresql() -> bool:
    bind = op.get_bind()
    return bool(bind and bind.dialect.name == 'postgresql')


def upgrade():
    if not _is_postgresql():
        return

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_attachment_ocr_text_fts
        ON attachment
        USING GIN (to_tsvector('portuguese', coalesce(ocr_text, '')));
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_article_texto_fts
        ON article
        USING GIN (to_tsvector('portuguese', coalesce(texto, '')));
        """
    )


def downgrade():
    if not _is_postgresql():
        return

    op.execute("DROP INDEX IF EXISTS ix_article_texto_fts;")
    op.execute("DROP INDEX IF EXISTS ix_attachment_ocr_text_fts;")
