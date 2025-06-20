"""drop legacy role-based tables"""

from alembic import op
import sqlalchemy as sa

revision = 'f5c6d7e8a9b0'
down_revision = 'e3b1a2c4d5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Remove tables from the old role-based display system if they exist
    for table in ['legacy_role', 'legacy_role_permissions']:
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')


def downgrade():
    # Recreate placeholder tables in case of downgrade
    op.create_table(
        'legacy_role',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False)
    )
    op.create_table(
        'legacy_role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('role_id', 'permission')
    )
    op.create_foreign_key(None, 'legacy_role_permissions', 'legacy_role', ['role_id'], ['id'])
