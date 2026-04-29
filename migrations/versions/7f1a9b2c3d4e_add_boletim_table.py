"""add boletim table with ocr fields and fts index

Revision ID: 7f1a9b2c3d4e
Revises: 2aa4d61d9b20
Create Date: 2026-04-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f1a9b2c3d4e'
down_revision = '2aa4d61d9b20'
branch_labels = None
depends_on = None


def _is_postgresql() -> bool:
    bind = op.get_bind()
    return bool(bind and bind.dialect.name == 'postgresql')


def upgrade():
    op.create_table(
        'boletim',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('data_boletim', sa.Date(), nullable=False),
        sa.Column('arquivo', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('ocr_status', sa.String(length=32), nullable=False, server_default='nao_aplicavel'),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('ocr_processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_error_message', sa.Text(), nullable=True),
        sa.Column('ocr_page_count', sa.Integer(), nullable=True),
        sa.Column('ocr_pages_success', sa.Integer(), nullable=True),
        sa.Column('ocr_pages_failed', sa.Integer(), nullable=True),
        sa.Column('ocr_char_count', sa.Integer(), nullable=True),
        sa.Column('ocr_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ocr_last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_confidence_score', sa.Float(), nullable=True),
        sa.Column('ocr_engine', sa.String(length=64), nullable=True),
        sa.Column('ocr_processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('ocr_requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_last_error', sa.Text(), nullable=True),
    )

    op.create_index('ix_boletim_titulo', 'boletim', ['titulo'])
    op.create_index('ix_boletim_data_boletim', 'boletim', ['data_boletim'])

    if _is_postgresql():
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_boletim_ocr_text_fts
            ON boletim
            USING GIN (to_tsvector('portuguese', coalesce(ocr_text, '')));
            """
        )


def downgrade():
    if _is_postgresql():
        op.execute("DROP INDEX IF EXISTS ix_boletim_ocr_text_fts;")

    op.drop_index('ix_boletim_data_boletim', table_name='boletim')
    op.drop_index('ix_boletim_titulo', table_name='boletim')
    op.drop_table('boletim')
