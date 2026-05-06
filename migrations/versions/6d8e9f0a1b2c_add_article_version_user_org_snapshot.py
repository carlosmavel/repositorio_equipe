"""add article version user org snapshot fields

Revision ID: 6d8e9f0a1b2c
Revises: b4c7d9e1f2a3
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d8e9f0a1b2c'
down_revision = 'b4c7d9e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('article_version', sa.Column('changed_by_cargo_nome', sa.String(length=200), nullable=True))
    op.add_column('article_version', sa.Column('changed_by_setor_nome', sa.String(length=200), nullable=True))
    op.add_column('article_version', sa.Column('changed_by_celula_nome', sa.String(length=200), nullable=True))
    op.add_column('article_version', sa.Column('changed_by_estabelecimento_nome_fantasia', sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column('article_version', 'changed_by_estabelecimento_nome_fantasia')
    op.drop_column('article_version', 'changed_by_celula_nome')
    op.drop_column('article_version', 'changed_by_setor_nome')
    op.drop_column('article_version', 'changed_by_cargo_nome')
