"""add default hierarchy tables for cargo"""

from alembic import op
import sqlalchemy as sa

revision = 'c1a2b3c4d5e6'
down_revision = 'afda22a0d5fb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cargo_default_celulas',
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('celula_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id']),
        sa.ForeignKeyConstraint(['celula_id'], ['celula.id']),
        sa.PrimaryKeyConstraint('cargo_id', 'celula_id')
    )
    op.create_table(
        'cargo_default_setores',
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('setor_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id']),
        sa.ForeignKeyConstraint(['setor_id'], ['setor.id']),
        sa.PrimaryKeyConstraint('cargo_id', 'setor_id')
    )


def downgrade():
    op.drop_table('cargo_default_setores')
    op.drop_table('cargo_default_celulas')
