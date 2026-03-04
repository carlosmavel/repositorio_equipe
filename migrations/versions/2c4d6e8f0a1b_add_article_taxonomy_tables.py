"""add article taxonomy tables

Revision ID: 2c4d6e8f0a1b
Revises: 0b1c2d3e4f67
Create Date: 2026-03-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '2c4d6e8f0a1b'
down_revision = '0b1c2d3e4f67'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'artigo_tipo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_table(
        'artigo_area_sistema',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.add_column('article', sa.Column('tipo_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('area_sistema_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_article_tipo_id', 'article', 'artigo_tipo', ['tipo_id'], ['id'])
    op.create_foreign_key('fk_article_area_sistema_id', 'article', 'artigo_area_sistema', ['area_sistema_id'], ['id'])

    op.execute(
        sa.text(
            """
            INSERT INTO funcao (codigo, nome)
            VALUES
                ('artigo_tipo_gerenciar', 'Gerenciar tipos de artigo'),
                ('artigo_area_gerenciar', 'Gerenciar áreas/sistemas de artigo')
            ON CONFLICT (codigo) DO NOTHING
            """
        )
    )


def downgrade():
    op.execute(sa.text("DELETE FROM funcao WHERE codigo IN ('artigo_tipo_gerenciar', 'artigo_area_gerenciar')"))
    op.drop_constraint('fk_article_area_sistema_id', 'article', type_='foreignkey')
    op.drop_constraint('fk_article_tipo_id', 'article', type_='foreignkey')
    op.drop_column('article', 'area_sistema_id')
    op.drop_column('article', 'tipo_id')
    op.drop_table('artigo_area_sistema')
    op.drop_table('artigo_tipo')
