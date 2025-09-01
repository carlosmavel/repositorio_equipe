"""add fields to campo_formulario"""

from alembic import op
import sqlalchemy as sa

revision = '3e4f5g6h7i8j'
down_revision = '2f1a2b3c4d5e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('campo_formulario', 'obrigatorio', new_column_name='obrigatoria')
    op.add_column('campo_formulario', sa.Column('subtitulo', sa.String(length=200), nullable=True))
    op.add_column('campo_formulario', sa.Column('midia_url', sa.String(length=255), nullable=True))
    op.add_column('campo_formulario', sa.Column('permite_multipla_escolha', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('campo_formulario', sa.Column('usar_menu_suspenso', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('campo_formulario', sa.Column('embaralhar_opcoes', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('campo_formulario', sa.Column('tem_opcao_outra', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('campo_formulario', sa.Column('ramificacoes', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('campo_formulario', 'ramificacoes')
    op.drop_column('campo_formulario', 'tem_opcao_outra')
    op.drop_column('campo_formulario', 'embaralhar_opcoes')
    op.drop_column('campo_formulario', 'usar_menu_suspenso')
    op.drop_column('campo_formulario', 'permite_multipla_escolha')
    op.drop_column('campo_formulario', 'midia_url')
    op.drop_column('campo_formulario', 'subtitulo')
    op.alter_column('campo_formulario', 'obrigatoria', new_column_name='obrigatorio')
