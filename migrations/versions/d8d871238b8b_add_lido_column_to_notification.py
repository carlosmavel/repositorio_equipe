"""Add lido column to Notification

Revision ID: d8d871238b8b
Revises: 2069a2357843
Create Date: 2025-05-20 18:XX:XX.XXXXXX
"""
from alembic import op
import sqlalchemy as sa

# identifiers, used by Alembic.
revision = 'd8d871238b8b'
down_revision = '2069a2357843'
branch_labels = None
depends_on = None

def upgrade():
    # adiciona coluna lido com default false para não quebrar em dados existentes
    op.add_column(
        'notification',
        sa.Column(
            'lido',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )
    # remove o default se quiser, mas não é obrigatório:
    # op.alter_column('notification', 'lido', server_default=None)

def downgrade():
    op.drop_column('notification', 'lido')