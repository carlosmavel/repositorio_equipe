"""add ocr reprocess audit table

Revision ID: c7a1d9e6b2f4
Revises: fb34c1d2e3a4
Create Date: 2026-04-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7a1d9e6b2f4'
down_revision = 'fb34c1d2e3a4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ocr_reprocess_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('attachment_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=False),
        sa.Column('trigger_scope', sa.String(length=32), nullable=False),
        sa.Column('previous_status', sa.String(length=32), nullable=True),
        sa.Column('new_status', sa.String(length=32), nullable=False, server_default='pendente'),
        sa.Column('attempts_before', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('attempts_after', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['article_id'], ['article.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attachment_id'], ['attachment.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_reprocess_audit_attachment_id'), 'ocr_reprocess_audit', ['attachment_id'], unique=False)
    op.create_index(op.f('ix_ocr_reprocess_audit_article_id'), 'ocr_reprocess_audit', ['article_id'], unique=False)
    op.create_index(op.f('ix_ocr_reprocess_audit_triggered_at'), 'ocr_reprocess_audit', ['triggered_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_ocr_reprocess_audit_triggered_at'), table_name='ocr_reprocess_audit')
    op.drop_index(op.f('ix_ocr_reprocess_audit_article_id'), table_name='ocr_reprocess_audit')
    op.drop_index(op.f('ix_ocr_reprocess_audit_attachment_id'), table_name='ocr_reprocess_audit')
    op.drop_table('ocr_reprocess_audit')
