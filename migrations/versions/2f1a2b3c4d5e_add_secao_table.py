"""add secao table and campo_formulario.secao_id

Revision ID: 2f1a2b3c4d5e
Revises: 1a2b3c4d5e7f
Create Date: 2025-06-02 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '2f1a2b3c4d5e'
down_revision = '1a2b3c4d5e7f'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'secao',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('formulario_id', sa.Integer(), sa.ForeignKey('formulario.id'), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=True),
        sa.Column('subtitulo', sa.String(length=200), nullable=True),
        sa.Column('imagem_url', sa.String(length=255), nullable=True),
        sa.Column('video_url', sa.String(length=255), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=False)
    )
    op.add_column('campo_formulario', sa.Column('secao_id', sa.Integer(), nullable=True))
    op.create_foreign_key('campo_formulario_secao_id_fkey', 'campo_formulario', 'secao', ['secao_id'], ['id'])

def downgrade():
    op.drop_constraint('campo_formulario_secao_id_fkey', 'campo_formulario', type_='foreignkey')
    op.drop_column('campo_formulario', 'secao_id')
    op.drop_table('secao')
