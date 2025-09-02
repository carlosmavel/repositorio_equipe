"""fix ordem_servico.tipo_os foreign key"""

from alembic import op
import sqlalchemy as sa


def _has_fk(table: str, constraint: str) -> bool:
    """Return True if the given FK constraint exists on the table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fks = {fk["name"].lower() for fk in inspector.get_foreign_keys(table)}
    return constraint.lower() in fks


def _fk_names(table: str, column: str) -> list[str]:
    """Return FK names that constrain the given column on the table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names: list[str] = []
    for fk in inspector.get_foreign_keys(table):
        cols = [c.lower() for c in fk["constrained_columns"]]
        if column.lower() in cols:
            names.append(fk["name"])
    return names


# revision identifiers, used by Alembic.
revision = '6b6b76d9b5e5'
down_revision = 'c2d1e3f4a567'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        # Drop any existing FKs on tipo_os_id before altering type
        for fk_name in _fk_names('ordem_servico', 'tipo_os_id'):
            batch_op.drop_constraint(fk_name, type_='foreignkey')


        # Alter column type to Integer
        batch_op.alter_column(
            'tipo_os_id',
            existing_type=sa.String(length=36),
            type_=sa.Integer(),
            existing_nullable=False,
        )

        # Create new FK to tipo_os only if missing
        if not _has_fk('ordem_servico', 'ordem_servico_tipo_os_id_fkey'):
            batch_op.create_foreign_key(
                'ordem_servico_tipo_os_id_fkey', 'tipo_os', ['tipo_os_id'], ['id']
            )

def downgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        for fk_name in _fk_names('ordem_servico', 'tipo_os_id'):
            batch_op.drop_constraint(fk_name, type_='foreignkey')

        batch_op.alter_column(
            'tipo_os_id',
            existing_type=sa.Integer(),
            type_=sa.String(length=36),
            existing_nullable=False,
        )

        if not _has_fk('ordem_servico', 'ordem_servico_processo_id_fkey'):
            batch_op.create_foreign_key(
                'ordem_servico_processo_id_fkey', 'processo', ['tipo_os_id'], ['id']
            )
