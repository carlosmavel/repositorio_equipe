"""split artigo area/sistema into separate taxonomies

Revision ID: 3a4b5c6d7e8f
Revises: 2c4d6e8f0a1b
Create Date: 2026-03-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '3a4b5c6d7e8f'
down_revision = '2c4d6e8f0a1b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'artigo_area',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_table(
        'artigo_sistema',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )

    op.add_column('article', sa.Column('area_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('sistema_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_article_area_id', 'article', 'artigo_area', ['area_id'], ['id'])
    op.create_foreign_key('fk_article_sistema_id', 'article', 'artigo_sistema', ['sistema_id'], ['id'])

    op.execute(
        sa.text(
            """
            INSERT INTO artigo_area (nome, descricao, ativo)
            SELECT nome, descricao, ativo
            FROM artigo_area_sistema
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO artigo_sistema (nome, descricao, ativo)
            SELECT nome, descricao, ativo
            FROM artigo_area_sistema
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE article a
            SET area_id = aa.id,
                sistema_id = asi.id
            FROM artigo_area_sistema old
            LEFT JOIN artigo_area aa ON aa.nome = old.nome
            LEFT JOIN artigo_sistema asi ON asi.nome = old.nome
            WHERE a.area_sistema_id = old.id
            """
        )
    )

    op.drop_constraint('fk_article_area_sistema_id', 'article', type_='foreignkey')
    op.drop_column('article', 'area_sistema_id')
    op.drop_table('artigo_area_sistema')


def downgrade():
    op.create_table(
        'artigo_area_sistema',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )

    op.add_column('article', sa.Column('area_sistema_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_article_area_sistema_id', 'article', 'artigo_area_sistema', ['area_sistema_id'], ['id'])

    op.execute(
        sa.text(
            """
            INSERT INTO artigo_area_sistema (nome, descricao, ativo)
            SELECT nome, descricao, ativo FROM artigo_area
            ON CONFLICT (nome) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO artigo_area_sistema (nome, descricao, ativo)
            SELECT nome, descricao, ativo FROM artigo_sistema
            ON CONFLICT (nome) DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE article a
            SET area_sistema_id = aas.id
            FROM artigo_area aa
            JOIN artigo_area_sistema aas ON aas.nome = aa.nome
            WHERE a.area_id = aa.id
            """
        )
    )

    op.drop_constraint('fk_article_sistema_id', 'article', type_='foreignkey')
    op.drop_constraint('fk_article_area_id', 'article', type_='foreignkey')
    op.drop_column('article', 'sistema_id')
    op.drop_column('article', 'area_id')
    op.drop_table('artigo_sistema')
    op.drop_table('artigo_area')
