"""add sequence for article id"""

from alembic import op
import sqlalchemy as sa

revision = 'c4f9b8e3d7a1'
down_revision = '0b1c2d3e4f67'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        start_id = bind.execute(
            sa.text("SELECT NVL(MAX(id), 0) + 1 FROM article")
        ).scalar()
        op.execute(sa.text(f"CREATE SEQUENCE article_id_seq START WITH {start_id}"))

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        op.execute(sa.text("DROP SEQUENCE article_id_seq"))
