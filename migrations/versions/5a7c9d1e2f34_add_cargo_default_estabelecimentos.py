"""add cargo default estabelecimentos table

Revision ID: 5a7c9d1e2f34
Revises: 4d5e6f7a8b9c
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a7c9d1e2f34'
down_revision = '4d5e6f7a8b9c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cargo_default_estabelecimentos',
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('estabelecimento_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id']),
        sa.ForeignKeyConstraint(['estabelecimento_id'], ['estabelecimento.id']),
        sa.PrimaryKeyConstraint('cargo_id', 'estabelecimento_id'),
    )


def downgrade():
    op.drop_table('cargo_default_estabelecimentos')
