"""remove role column from user"""

from alembic import op
import sqlalchemy as sa

revision = 'e3b1a2c4d5f6'
down_revision = 'd9c4b82b9ae3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('role')


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=50), nullable=False, server_default='colaborador'))
