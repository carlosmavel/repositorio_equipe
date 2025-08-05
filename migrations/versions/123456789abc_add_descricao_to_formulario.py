"""add descricao column to formulario

Revision ID: 123456789abc
Revises: 3e4f5g6h7i8j
Create Date: 2025-08-05 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '123456789abc'
down_revision = '3e4f5g6h7i8j'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('formulario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('descricao', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('formulario', schema=None) as batch_op:
        batch_op.drop_column('descricao')
