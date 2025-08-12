"""add status to sistema table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3b2c1d4e5f6'
down_revision = '1d2e3f4g5h7i'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('sistema', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=False, server_default='Ativo'))


def downgrade():
    with op.batch_alter_table('sistema', schema=None) as batch_op:
        batch_op.drop_column('status')
