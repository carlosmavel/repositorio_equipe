"""Add tipo column to comentario"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_comment_tipo'
down_revision = '0002_add_article_id_sequence'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'comentario',
        sa.Column('tipo', sa.String(length=30), nullable=False, server_default='Aprovação')
    )


def downgrade():
    op.drop_column('comentario', 'tipo')
