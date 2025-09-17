"""Add ativo column to Instituicao

Revision ID: 9e9642d233f1
Revises: 8f36375399a9
Create Date: 2025-06-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9e9642d233f1'
down_revision = '8f36375399a9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('instituicao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    with op.batch_alter_table('instituicao', schema=None) as batch_op:
        batch_op.drop_column('ativo')
