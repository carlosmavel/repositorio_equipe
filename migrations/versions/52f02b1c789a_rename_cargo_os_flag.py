"""rename atende_ordem_servico to pode_atender_os

Revision ID: 52f02b1c789a
Revises: ab12cd34ef56
Create Date: 2025-08-09 00:00:00
"""

from alembic import op
import sqlalchemy as sa


def _has_column(table: str, column: str) -> bool:
    """Return True if the given table has the specified column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}

# revision identifiers, used by Alembic.
revision = '52f02b1c789a'
down_revision = 'ab12cd34ef56'
branch_labels = None
depends_on = None


def upgrade():
    if _has_column('cargo', 'atende_ordem_servico'):
        if _has_column('cargo', 'pode_atender_os'):
            op.drop_column('cargo', 'atende_ordem_servico')
        else:
            with op.batch_alter_table('cargo') as batch_op:
                batch_op.alter_column('atende_ordem_servico', new_column_name='pode_atender_os')


def downgrade():
    if _has_column('cargo', 'pode_atender_os'):
        if _has_column('cargo', 'atende_ordem_servico'):
            op.drop_column('cargo', 'pode_atender_os')
        else:
            with op.batch_alter_table('cargo') as batch_op:
                batch_op.alter_column('pode_atender_os', new_column_name='atende_ordem_servico')
