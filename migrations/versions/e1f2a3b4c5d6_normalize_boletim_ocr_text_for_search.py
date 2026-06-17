"""normalize boletim ocr text for search

Revision ID: e1f2a3b4c5d6
Revises: bd72a3f4c9e8
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op


revision = 'e1f2a3b4c5d6'
down_revision = 'bd72a3f4c9e8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        op.execute(
            r"""
            UPDATE boletim
            SET
                ocr_text = btrim(regexp_replace(coalesce(ocr_text, ''), '\s+', ' ', 'g')),
                ocr_char_count = char_length(btrim(regexp_replace(coalesce(ocr_text, ''), '\s+', ' ', 'g'))),
                search_text_normalized = lower(
                    unaccent(
                        regexp_replace(
                            coalesce(titulo, '') || ' ' || btrim(regexp_replace(coalesce(ocr_text, ''), '\s+', ' ', 'g')),
                            '\s+',
                            ' ',
                            'g'
                        )
                    )
                )
            WHERE ocr_text IS NOT NULL
            """
        )
    else:
        # Backfill completo de whitespace usa regexp_replace nativo do PostgreSQL,
        # que é o banco de produção suportado para os índices de busca.
        pass


def downgrade():
    # Não há restauração segura do texto OCR bruto após a normalização.
    pass
