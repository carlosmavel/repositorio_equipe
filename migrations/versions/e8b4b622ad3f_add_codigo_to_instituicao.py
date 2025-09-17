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
    op.add_column('instituicao', sa.Column('codigo', sa.String(length=7), nullable=True))
    op.execute("UPDATE instituicao SET codigo = 'TEMP001' WHERE codigo IS NULL")
    op.alter_column('instituicao', 'codigo', nullable=False)


def downgrade():
    op.drop_column('instituicao', 'codigo')
