"""fix ordem_servico.tipo_os foreign key"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6b6b76d9b5e5'
down_revision = 'c2d1e3f4a567'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        # Drop old FK pointing to processo
        batch_op.drop_constraint('ordem_servico_processo_id_fkey', type_='foreignkey')
        # Alter column type to Integer
        batch_op.alter_column(
            'tipo_os_id',
            existing_type=sa.String(length=36),
            type_=sa.Integer(),
            existing_nullable=False,
        )
        # Create new FK to tipo_os
        batch_op.create_foreign_key(
            'ordem_servico_tipo_os_id_fkey', 'tipo_os', ['tipo_os_id'], ['id']
        )

def downgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.drop_constraint('ordem_servico_tipo_os_id_fkey', type_='foreignkey')
        batch_op.alter_column(
            'tipo_os_id',
            existing_type=sa.Integer(),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
        batch_op.create_foreign_key(
            'ordem_servico_processo_id_fkey', 'processo', ['tipo_os_id'], ['id']
        )
