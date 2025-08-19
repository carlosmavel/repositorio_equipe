"""add creator and celula to formulario"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3f1a2b4c5e6'
down_revision = 'a3b2c1d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('formulario', sa.Column('criado_por_id', sa.Integer(), nullable=False))
    op.add_column('formulario', sa.Column('celula_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_formulario_criado_por', 'formulario', 'user', ['criado_por_id'], ['id'])
    op.create_foreign_key('fk_formulario_celula', 'formulario', 'celula', ['celula_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_formulario_celula', 'formulario', type_='foreignkey')
    op.drop_constraint('fk_formulario_criado_por', 'formulario', type_='foreignkey')
    op.drop_column('formulario', 'celula_id')
    op.drop_column('formulario', 'criado_por_id')

