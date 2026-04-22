"""make user organizational links nullable

Revision ID: 3c1d2e4f5a6b
Revises: 9f7a6b5c4d3e
Create Date: 2026-04-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c1d2e4f5a6b'
down_revision = '9f7a6b5c4d3e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('user', 'estabelecimento_id', existing_type=sa.Integer(), nullable=True)
    op.alter_column('user', 'setor_id', existing_type=sa.Integer(), nullable=True)
    op.alter_column('user', 'celula_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    op.alter_column('user', 'celula_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('user', 'setor_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('user', 'estabelecimento_id', existing_type=sa.Integer(), nullable=False)
