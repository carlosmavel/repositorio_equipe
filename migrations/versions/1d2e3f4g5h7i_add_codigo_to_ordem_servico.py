"""add codigo column to ordem_servico"""

from alembic import op
import sqlalchemy as sa

revision = '1d2e3f4g5h7i'
down_revision = '1c2d3e4f5g7h'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ordem_servico', sa.Column('codigo', sa.String(length=7), nullable=True))

    conn = op.get_bind()
    ordem_servico = sa.table(
        'ordem_servico',
        sa.column('id', sa.String(36)),
        sa.column('codigo', sa.String(7)),
        sa.column('data_criacao', sa.DateTime),
    )
    result = conn.execute(sa.select(ordem_servico.c.id).order_by(ordem_servico.c.data_criacao))
    prefixo = 'A'
    numero = 1
    for row in result:
        codigo = f"{prefixo}{numero:06d}"
        numero += 1
        conn.execute(
            ordem_servico.update().where(ordem_servico.c.id == row.id).values(codigo=codigo)
        )

    op.alter_column('ordem_servico', 'codigo', nullable=False)
    op.create_unique_constraint('uq_ordem_servico_codigo', 'ordem_servico', ['codigo'])


def downgrade():
    op.drop_constraint('uq_ordem_servico_codigo', 'ordem_servico', type_='unique')
    op.drop_column('ordem_servico', 'codigo')
