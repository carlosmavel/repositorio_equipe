"""add codigo to instituicao

Revision ID: e8b4b622ad3f
Revises: abcdef123456
Create Date: 2025-08-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e8b4b622ad3f'
down_revision = 'abcdef123456'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('instituicao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('codigo', sa.String(length=7), nullable=False))
        batch_op.create_unique_constraint(None, ['codigo'])


def downgrade():
    with op.batch_alter_table('instituicao', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('codigo')
