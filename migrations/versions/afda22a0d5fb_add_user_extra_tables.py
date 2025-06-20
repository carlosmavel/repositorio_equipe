"""add tables for user extra setores and celulas"""

from alembic import op
import sqlalchemy as sa

revision = 'afda22a0d5fb'
down_revision = 'b9bcef2efe2d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_extra_celulas',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('celula_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['celula_id'], ['celula.id']),
        sa.PrimaryKeyConstraint('user_id', 'celula_id')
    )
    op.create_table(
        'user_extra_setores',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('setor_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['setor_id'], ['setor.id']),
        sa.PrimaryKeyConstraint('user_id', 'setor_id')
    )


def downgrade():
    op.drop_table('user_extra_setores')
    op.drop_table('user_extra_celulas')
