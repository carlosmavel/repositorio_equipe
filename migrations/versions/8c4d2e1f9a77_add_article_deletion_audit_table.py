"""add article deletion audit table

Revision ID: 8c4d2e1f9a77
Revises: 9f7a1b2c3d4e
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c4d2e1f9a77'
down_revision = '9f7a1b2c3d4e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'article_deletion_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('article_title', sa.String(length=200), nullable=False),
        sa.Column('deleted_by_user_id', sa.Integer(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('attachment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['deleted_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_article_deletion_audit_article_id'), 'article_deletion_audit', ['article_id'], unique=False)
    op.create_index(op.f('ix_article_deletion_audit_deleted_at'), 'article_deletion_audit', ['deleted_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_article_deletion_audit_deleted_at'), table_name='article_deletion_audit')
    op.drop_index(op.f('ix_article_deletion_audit_article_id'), table_name='article_deletion_audit')
    op.drop_table('article_deletion_audit')
