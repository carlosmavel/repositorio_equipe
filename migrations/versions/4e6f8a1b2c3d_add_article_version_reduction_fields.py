"""add explicit article version reduction fields

Revision ID: 4e6f8a1b2c3d
Revises: a7c5d3e9f012
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '4e6f8a1b2c3d'
down_revision = 'a7c5d3e9f012'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('article_version', sa.Column('previous_char_count', sa.Integer(), nullable=True))
    op.add_column('article_version', sa.Column('new_char_count', sa.Integer(), nullable=True))
    op.add_column('article_version', sa.Column('reduction_percent', sa.Float(), nullable=True))
    op.add_column(
        'article_version',
        sa.Column('drastic_reduction', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.execute(
        """
        UPDATE article_version
        SET previous_char_count = previous_text_char_count,
            new_char_count = text_char_count,
            reduction_percent = text_reduction_percent,
            drastic_reduction = drastic_reduction_detected
        """
    )


def downgrade():
    op.drop_column('article_version', 'drastic_reduction')
    op.drop_column('article_version', 'reduction_percent')
    op.drop_column('article_version', 'new_char_count')
    op.drop_column('article_version', 'previous_char_count')
