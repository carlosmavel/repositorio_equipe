"""add deve_trocar_senha to user

Revision ID: 9f7a6b5c4d3e
Revises: 3a4b5c6d7e8f
Create Date: 2026-04-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f7a6b5c4d3e'
down_revision = '3a4b5c6d7e8f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('deve_trocar_senha', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade():
    op.drop_column('user', 'deve_trocar_senha')
