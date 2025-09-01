"""add ativo column to formulario

Revision ID: 7c8d9e0f1a2b
Revises: 123456789abc
Create Date: 2025-07-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7c8d9e0f1a2b'
down_revision = '123456789abc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('formulario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade():
    with op.batch_alter_table('formulario', schema=None) as batch_op:
        batch_op.drop_column('ativo')
