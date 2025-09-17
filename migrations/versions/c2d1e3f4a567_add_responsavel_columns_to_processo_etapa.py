"""Add responsavel fields to processo_etapa"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2d1e3f4a567'
down_revision = 'ea3b24d8f6c7'
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    return column_name in cols


def upgrade():
    if not _has_column('processo_etapa', 'setor_responsavel_id'):
        op.add_column('processo_etapa', sa.Column('setor_responsavel_id', sa.Integer(), nullable=True))
        op.create_foreign_key('processo_etapa_setor_responsavel_id_fkey', 'processo_etapa', 'setor', ['setor_responsavel_id'], ['id'])
    if not _has_column('processo_etapa', 'celula_responsavel_id'):
        op.add_column('processo_etapa', sa.Column('celula_responsavel_id', sa.Integer(), nullable=True))
        op.create_foreign_key('processo_etapa_celula_responsavel_id_fkey', 'processo_etapa', 'celula', ['celula_responsavel_id'], ['id'])
    if not _has_column('processo_etapa', 'descricao'):
        op.add_column('processo_etapa', sa.Column('descricao', sa.Text(), nullable=True))
    if not _has_column('processo_etapa', 'instrucoes'):
        op.add_column('processo_etapa', sa.Column('instrucoes', sa.Text(), nullable=True))


def downgrade():
    if _has_column('processo_etapa', 'instrucoes'):
        op.drop_column('processo_etapa', 'instrucoes')
    if _has_column('processo_etapa', 'descricao'):
        op.drop_column('processo_etapa', 'descricao')
    if _has_column('processo_etapa', 'celula_responsavel_id'):
        op.drop_constraint('processo_etapa_celula_responsavel_id_fkey', 'processo_etapa', type_='foreignkey')
        op.drop_column('processo_etapa', 'celula_responsavel_id')
    if _has_column('processo_etapa', 'setor_responsavel_id'):
        op.drop_constraint('processo_etapa_setor_responsavel_id_fkey', 'processo_etapa', type_='foreignkey')
        op.drop_column('processo_etapa', 'setor_responsavel_id')
