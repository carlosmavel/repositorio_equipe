"""add process tables

Revision ID: 09981b61c779
Revises: fa23b0c1c9d0
Create Date: 2025-08-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '09981b61c779'
down_revision = 'fa23b0c1c9d0'
branch_labels = None
depends_on = None


def upgrade():
    # 1) create processo table
    op.create_table(
        'processo',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )

    # 2) etapa_processo table
    op.create_table(
        'etapa_processo',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('processo_id', sa.String(length=36), sa.ForeignKey('processo.id'), nullable=False),
        sa.Column('cargo_id', sa.Integer(), sa.ForeignKey('cargo.id'), nullable=True),
        sa.Column('setor_id', sa.Integer(), sa.ForeignKey('setor.id'), nullable=True),
        sa.Column('obrigatoria', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )

    # 3) campo_etapa table
    op.create_table(
        'campo_etapa',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('etapa_id', sa.String(length=36), sa.ForeignKey('etapa_processo.id'), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('obrigatorio', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('opcoes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('dica', sa.String(length=255), nullable=True),
    )

    # 4) resposta_etapa_os table
    op.create_table(
        'resposta_etapa_os',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('ordem_servico_id', sa.String(length=36), nullable=False),
        sa.Column('campo_etapa_id', sa.String(length=36), sa.ForeignKey('campo_etapa.id'), nullable=False),
        sa.Column('valor', sa.Text(), nullable=True),
        sa.Column('preenchido_por', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('data_hora', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )


def downgrade():
    op.drop_table('resposta_etapa_os')
    op.drop_table('campo_etapa')
    op.drop_table('etapa_processo')
    op.drop_table('processo')
