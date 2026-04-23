"""rename atende_ordem_servico to pode_atender_os

Revision ID: 52f02b1c789a
Revises: ab12cd34ef56
Create Date: 2025-08-09 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '52f02b1c789a'
down_revision = 'ab12cd34ef56'
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col['name'] == column_name for col in inspector.get_columns(table_name))


def upgrade():
    has_old_column = _column_exists('cargo', 'atende_ordem_servico')
    has_new_column = _column_exists('cargo', 'pode_atender_os')

    if has_old_column and not has_new_column:
        with op.batch_alter_table('cargo') as batch_op:
            batch_op.alter_column('atende_ordem_servico', new_column_name='pode_atender_os')
    elif has_new_column:
        # A coluna nova já existe (ex.: base criada com migration mais recente); nada a fazer.
        pass
    else:
        # Estado inesperado em bases antigas/inconsistentes: garante a coluna prevista pela release.
        with op.batch_alter_table('cargo') as batch_op:
            batch_op.add_column(sa.Column('pode_atender_os', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    has_old_column = _column_exists('cargo', 'atende_ordem_servico')
    has_new_column = _column_exists('cargo', 'pode_atender_os')

    if has_new_column and not has_old_column:
        with op.batch_alter_table('cargo') as batch_op:
            batch_op.alter_column('pode_atender_os', new_column_name='atende_ordem_servico')
    elif has_old_column:
        # A coluna antiga já existe; downgrade já está refletido.
        pass
    else:
        # Mantém downgrade resiliente em cenários inconsistentes.
        with op.batch_alter_table('cargo') as batch_op:
            batch_op.add_column(sa.Column('atende_ordem_servico', sa.Boolean(), nullable=False, server_default='false'))
