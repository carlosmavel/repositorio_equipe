"""enforce diagram deletion and retention policy

Revision ID: e7a9c1d3f5b7
Revises: d6f8a0b2c4e6
"""

from alembic import op
import sqlalchemy as sa


revision = 'e7a9c1d3f5b7'
down_revision = 'd6f8a0b2c4e6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('diagram', sa.Column('archived_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_diagram_archived_by_user_id_user', 'diagram', 'user',
        ['archived_by_user_id'], ['id'], ondelete='RESTRICT',
    )
    op.create_index('ix_diagram_archived_by_user_id', 'diagram', ['archived_by_user_id'])

    for table, constraint in (
        ('diagram_version', 'fk_diagram_version_diagram_id'),
        ('diagram_asset', 'fk_diagram_asset_diagram_id'),
    ):
        op.drop_constraint(constraint, table, type_='foreignkey')
        op.create_foreign_key(constraint, table, 'diagram', ['diagram_id'], ['id'], ondelete='RESTRICT')


def downgrade():
    for table, constraint in (
        ('diagram_version', 'fk_diagram_version_diagram_id'),
        ('diagram_asset', 'fk_diagram_asset_diagram_id'),
    ):
        op.drop_constraint(constraint, table, type_='foreignkey')
        op.create_foreign_key(constraint, table, 'diagram', ['diagram_id'], ['id'], ondelete='CASCADE')
    op.drop_index('ix_diagram_archived_by_user_id', table_name='diagram')
    op.drop_constraint('fk_diagram_archived_by_user_id_user', 'diagram', type_='foreignkey')
    op.drop_column('diagram', 'archived_by_user_id')
