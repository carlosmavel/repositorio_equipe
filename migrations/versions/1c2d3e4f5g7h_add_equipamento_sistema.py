"""add equipamento and sistema tables"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1c2d3e4f5g7h'
down_revision = 'e8b4b622ad3f'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'equipamento',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('patrimonio', sa.String(length=100), nullable=True),
        sa.Column('serial', sa.String(length=100), nullable=True),
        sa.Column('localizacao', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
    )
    op.create_table(
        'sistema',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(length=255), nullable=False, unique=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('responsavel', sa.String(length=255), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
    )
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.add_column(sa.Column('equipamento_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('sistema_id', sa.Integer(), nullable=True))
        batch_op.drop_column('origem')
        batch_op.create_foreign_key('ordem_servico_equipamento_id_fkey', 'equipamento', ['equipamento_id'], ['id'])
        batch_op.create_foreign_key('ordem_servico_sistema_id_fkey', 'sistema', ['sistema_id'], ['id'])


def downgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.drop_constraint('ordem_servico_equipamento_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('ordem_servico_sistema_id_fkey', type_='foreignkey')
        batch_op.add_column(sa.Column('origem', sa.String(length=255), nullable=True))
        batch_op.drop_column('equipamento_id')
        batch_op.drop_column('sistema_id')
    op.drop_table('sistema')
    op.drop_table('equipamento')
