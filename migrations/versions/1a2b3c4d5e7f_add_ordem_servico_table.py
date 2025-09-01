"""add ordem_servico table"""

from alembic import op
import sqlalchemy as sa

revision = '1a2b3c4d5e7f'
down_revision = '14f1ad31865d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ordem_servico',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('processo_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='aberta'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['processo_id'], ['processo.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('ordem_servico')

