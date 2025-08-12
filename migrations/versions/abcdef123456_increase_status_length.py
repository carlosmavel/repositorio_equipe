"""increase status column lengths"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = 'f1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(length=20), type_=sa.String(length=50))
    with op.batch_alter_table('ordem_servico_log') as batch_op:
        batch_op.alter_column('origem_status', existing_type=sa.String(length=20), type_=sa.String(length=50))
        batch_op.alter_column('destino_status', existing_type=sa.String(length=20), type_=sa.String(length=50))


def downgrade():
    with op.batch_alter_table('ordem_servico') as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(length=50), type_=sa.String(length=20))
    with op.batch_alter_table('ordem_servico_log') as batch_op:
        batch_op.alter_column('origem_status', existing_type=sa.String(length=50), type_=sa.String(length=20))
        batch_op.alter_column('destino_status', existing_type=sa.String(length=50), type_=sa.String(length=20))
