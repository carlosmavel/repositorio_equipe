"""add diagram version audit metadata

Revision ID: d6f8a0b2c4e6
Revises: c5e7f9a1b3d4
"""

from alembic import op
import sqlalchemy as sa


revision = 'd6f8a0b2c4e6'
down_revision = 'c5e7f9a1b3d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('diagram', sa.Column('updated_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_diagram_updated_by_user_id_user', 'diagram', 'user',
        ['updated_by_user_id'], ['id'], ondelete='RESTRICT',
    )
    op.create_index('ix_diagram_updated_by_user_id', 'diagram', ['updated_by_user_id'])
    op.add_column('diagram_version', sa.Column('reason', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('diagram_version', 'reason')
    op.drop_index('ix_diagram_updated_by_user_id', table_name='diagram')
    op.drop_constraint('fk_diagram_updated_by_user_id_user', 'diagram', type_='foreignkey')
    op.drop_column('diagram', 'updated_by_user_id')
