"""remove descricao and observacoes from ordem_servico"""

from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'd3f1a2b4c5e6'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.drop_column('descricao')
        batch_op.drop_column('observacoes')


def downgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.add_column(sa.Column('observacoes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('descricao', sa.Text(), nullable=False))
