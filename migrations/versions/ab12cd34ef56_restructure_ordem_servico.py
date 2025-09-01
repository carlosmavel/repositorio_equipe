"""restructure ordem servico

Revision ID: ab12cd34ef56
Revises: fa23b0c1c9d0
Create Date: 2025-07-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ab12cd34ef56'
down_revision = ('fa23b0c1c9d0', '7c8d9e0f1a2b')
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('ordem_servico', 'descricao', existing_type=sa.Text(), nullable=False)
    op.alter_column('ordem_servico', 'processo_id', new_column_name='tipo_os_id')
    op.alter_column('ordem_servico', 'tipo_os_id', existing_type=sa.String(length=36), nullable=False)
    op.alter_column(
        'ordem_servico',
        'status',
        existing_type=sa.String(length=20),
        existing_nullable=False,
        server_default='rascunho',
    )
    op.add_column('ordem_servico', sa.Column('criado_por_id', sa.Integer(), nullable=False))
    op.add_column('ordem_servico', sa.Column('atribuido_para_id', sa.Integer(), nullable=True))
    op.add_column('ordem_servico', sa.Column('equipe_responsavel_id', sa.Integer(), nullable=True))
    op.add_column('ordem_servico', sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))
    op.add_column('ordem_servico', sa.Column('data_conclusao', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ordem_servico', sa.Column('formulario_respostas_id', sa.Integer(), nullable=True))
    op.add_column('ordem_servico', sa.Column('prioridade', sa.String(length=10), nullable=True))
    op.add_column('ordem_servico', sa.Column('origem', sa.String(length=255), nullable=True))
    op.add_column('ordem_servico', sa.Column('observacoes', sa.Text(), nullable=True))
    op.drop_column('ordem_servico', 'created_at')
    op.drop_column('ordem_servico', 'updated_at')

    op.create_table(
        'ordem_servico_participante',
        sa.Column('ordem_servico_id', sa.String(length=36), sa.ForeignKey('ordem_servico.id'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), primary_key=True)
    )

    op.create_table(
        'ordem_servico_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('os_id', sa.String(length=36), sa.ForeignKey('ordem_servico.id'), nullable=False),
        sa.Column('data_hora', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('acao', sa.String(length=255), nullable=False),
        sa.Column('origem_status', sa.String(length=20)),
        sa.Column('destino_status', sa.String(length=20)),
        sa.Column('observacao', sa.Text())
    )

    op.create_table(
        'ordem_servico_comentario',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('os_id', sa.String(length=36), sa.ForeignKey('ordem_servico.id'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('data_hora', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('anexo', sa.String(length=255))
    )


def downgrade():
    op.drop_table('ordem_servico_comentario')
    op.drop_table('ordem_servico_log')
    op.drop_table('ordem_servico_participante')
    op.add_column('ordem_servico', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))
    op.add_column('ordem_servico', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False))
    op.drop_column('ordem_servico', 'observacoes')
    op.drop_column('ordem_servico', 'origem')
    op.drop_column('ordem_servico', 'prioridade')
    op.drop_column('ordem_servico', 'formulario_respostas_id')
    op.drop_column('ordem_servico', 'data_conclusao')
    op.drop_column('ordem_servico', 'data_criacao')
    op.drop_column('ordem_servico', 'equipe_responsavel_id')
    op.drop_column('ordem_servico', 'atribuido_para_id')
    op.drop_column('ordem_servico', 'criado_por_id')
    op.alter_column('ordem_servico', 'status', existing_type=sa.String(length=20), nullable=False, server_default='aberta')
    op.alter_column('ordem_servico', 'tipo_os_id', new_column_name='processo_id', existing_type=sa.String(length=36), nullable=True)
    op.alter_column('ordem_servico', 'descricao', existing_type=sa.Text(), nullable=True)
