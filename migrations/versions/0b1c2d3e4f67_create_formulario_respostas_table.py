"""create formulario_respostas table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0b1c2d3e4f67'
down_revision = ('d4e5f6a7b8c9', 'abcdef123456')
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'formulario_respostas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dados', sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        'ordem_servico_formulario_respostas_id_fkey',
        'ordem_servico',
        'formulario_respostas',
        ['formulario_respostas_id'],
        ['id']
    )


def downgrade():
    op.drop_constraint(
        'ordem_servico_formulario_respostas_id_fkey',
        'ordem_servico',
        type_='foreignkey'
    )
    op.drop_table('formulario_respostas')
