"""add ocr operational fields to attachment

Revision ID: c8d9e0f1a2b3
Revises: a1f0b3c9d2e4
Create Date: 2026-04-24 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8d9e0f1a2b3'
down_revision = 'a1f0b3c9d2e4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.alter_column('ocr_status', existing_type=sa.String(length=32), server_default='nao_aplicavel')
        batch_op.add_column(sa.Column('ocr_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ocr_processed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('ocr_error_message', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ocr_page_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ocr_pages_success', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ocr_pages_failed', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ocr_char_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ocr_last_attempt_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('ocr_confidence_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('ocr_engine', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('ocr_processing_time_seconds', sa.Float(), nullable=True))

    op.execute(
        """
        UPDATE attachment
           SET ocr_status = 'nao_aplicavel'
         WHERE (mime_type IS NULL OR lower(mime_type) <> 'application/pdf')
           AND (ocr_status IS NULL OR ocr_status = 'concluido');
        """
    )
    op.execute(
        """
        UPDATE attachment
           SET ocr_status = 'pendente'
         WHERE lower(coalesce(mime_type, '')) = 'application/pdf'
           AND (ocr_status IS NULL OR ocr_status = 'nao_aplicavel');
        """
    )

    op.create_index('ix_attachment_ocr_status', 'attachment', ['ocr_status'], unique=False)
    op.create_index('ix_attachment_ocr_last_attempt_at', 'attachment', ['ocr_last_attempt_at'], unique=False)
    op.create_index('ix_attachment_ocr_processed_at', 'attachment', ['ocr_processed_at'], unique=False)


def downgrade():
    op.drop_index('ix_attachment_ocr_processed_at', table_name='attachment')
    op.drop_index('ix_attachment_ocr_last_attempt_at', table_name='attachment')
    op.drop_index('ix_attachment_ocr_status', table_name='attachment')

    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.drop_column('ocr_processing_time_seconds')
        batch_op.drop_column('ocr_engine')
        batch_op.drop_column('ocr_confidence_score')
        batch_op.drop_column('ocr_last_attempt_at')
        batch_op.drop_column('ocr_char_count')
        batch_op.drop_column('ocr_pages_failed')
        batch_op.drop_column('ocr_pages_success')
        batch_op.drop_column('ocr_page_count')
        batch_op.drop_column('ocr_error_message')
        batch_op.drop_column('ocr_processed_at')
        batch_op.drop_column('ocr_text')
        batch_op.alter_column('ocr_status', existing_type=sa.String(length=32), server_default='concluido')
