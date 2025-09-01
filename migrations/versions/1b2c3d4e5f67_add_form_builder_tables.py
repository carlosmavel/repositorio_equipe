"""Add form builder tables and cargo flag

Revision ID: 1b2c3d4e5f67
Revises: 0d1288f8e4f7
Create Date: 2025-06-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1b2c3d4e5f67'
down_revision = '0d1288f8e4f7'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('cargo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pode_atender_os', sa.Boolean(), nullable=False, server_default=sa.text('0')))

    op.create_table(
        'formulario',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('estrutura', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'campo_formulario',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('formulario_id', sa.Integer(), sa.ForeignKey('formulario.id'), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=False),
        sa.Column('obrigatorio', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('opcoes', sa.Text(), nullable=True),
        sa.Column('condicional', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('campo_formulario')
    op.drop_table('formulario')
    with op.batch_alter_table('cargo', schema=None) as batch_op:
        batch_op.drop_column('pode_atender_os')
