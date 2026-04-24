"""add ocr queue fields to attachment

Revision ID: a1f0b3c9d2e4
Revises: 5a7c9d1e2f34
Create Date: 2026-04-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1f0b3c9d2e4'
down_revision = '5a7c9d1e2f34'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ocr_status', sa.String(length=32), nullable=False, server_default='concluido'))
        batch_op.add_column(sa.Column('ocr_attempts', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('ocr_requested_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('ocr_started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('ocr_finished_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('ocr_last_error', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.drop_column('ocr_last_error')
        batch_op.drop_column('ocr_finished_at')
        batch_op.drop_column('ocr_started_at')
        batch_op.drop_column('ocr_requested_at')
        batch_op.drop_column('ocr_attempts')
        batch_op.drop_column('ocr_status')
