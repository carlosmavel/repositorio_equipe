"""Drop centro_custo table and references"""

from alembic import op
import sqlalchemy as sa

revision = 'b21bf94c6932'
down_revision = '9e9642d233f1'
branch_labels = None
depends_on = None


def upgrade():
    """Remove columns referencing centro_custo and drop the table."""
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('centro_custo_id')

    with op.batch_alter_table('setor') as batch_op:
        batch_op.drop_column('centro_custo_id')

    with op.batch_alter_table('celula') as batch_op:
        batch_op.drop_column('centro_custo_id')

    op.drop_table('centro_custo')


def downgrade():
    # Recreate centro_custo table
    op.create_table(
        'centro_custo',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('estabelecimento_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['estabelecimento_id'], ['estabelecimento.id']),
        sa.UniqueConstraint('codigo')
    )

    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('centro_custo_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('user_centro_custo_id_fkey', 'centro_custo', ['centro_custo_id'], ['id'])

    with op.batch_alter_table('setor') as batch_op:
        batch_op.add_column(sa.Column('centro_custo_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('setor_centro_custo_id_fkey', 'centro_custo', ['centro_custo_id'], ['id'])

    with op.batch_alter_table('celula') as batch_op:
        batch_op.add_column(sa.Column('centro_custo_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('celula_centro_custo_id_fkey', 'centro_custo', ['centro_custo_id'], ['id'])

