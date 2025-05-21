"""Add rascunho to article_status enum

Revision ID: e6f8d2ffc333
Revises: bbc812bdfc13
Create Date: 2025-05-21 17:54:44.517036

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6f8d2ffc333'
down_revision = 'bbc812bdfc13'
branch_labels = None
depends_on = None


def upgrade():
    # adiciona o novo valor ao enum no Postgres
    op.execute("ALTER TYPE article_status ADD VALUE 'rascunho';")

def downgrade():
    # não dá pra remover valor de enum nativo no Postgres
    pass