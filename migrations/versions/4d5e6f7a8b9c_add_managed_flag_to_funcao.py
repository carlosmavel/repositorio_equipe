"""add managed flag to funcao

Revision ID: 4d5e6f7a8b9c
Revises: 3c1d2e4f5a6b
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d5e6f7a8b9c'
down_revision = '3c1d2e4f5a6b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'funcao',
        sa.Column('managed_by_system', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade():
    op.drop_column('funcao', 'managed_by_system')
