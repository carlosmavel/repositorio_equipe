"""add funcao and permission tables"""

from alembic import op
import sqlalchemy as sa

revision = 'd9c4b82b9ae3'
down_revision = 'c1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'funcao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=100), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    op.create_table(
        'cargo_funcoes',
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('funcao_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id']),
        sa.ForeignKeyConstraint(['funcao_id'], ['funcao.id']),
        sa.PrimaryKeyConstraint('cargo_id', 'funcao_id')
    )
    op.create_table(
        'user_funcoes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('funcao_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['funcao_id'], ['funcao.id']),
        sa.PrimaryKeyConstraint('user_id', 'funcao_id')
    )


def downgrade():
    op.drop_table('user_funcoes')
    op.drop_table('cargo_funcoes')
    op.drop_table('funcao')
