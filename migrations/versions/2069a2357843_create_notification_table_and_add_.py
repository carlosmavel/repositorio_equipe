"""Create notification table

Revision ID: 2069a2357843
Revises: 144bf20a903e
Create Date: 2025-05-20 17:20:55.348264
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2069a2357843'
down_revision = '144bf20a903e'
branch_labels = None
depends_on = None


def upgrade():
    # Cria apenas a tabela notification
    op.create_table(
        'notification',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )


def downgrade():
    # Remove apenas a tabela notification
    op.drop_table('notification')