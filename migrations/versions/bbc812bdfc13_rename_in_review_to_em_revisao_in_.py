"""Rename in_review to em_revisao in article_status

Revision ID: bbc812bdfc13
Revises: d8d871238b8b
Create Date: 2025-05-21 17:39:30.311240

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bbc812bdfc13'
down_revision = 'd8d871238b8b'
branch_labels = None
depends_on = None

def upgrade():
    # renomeia apenas o valor do enum
    op.execute("""
        ALTER TYPE article_status 
        RENAME VALUE 'in_review' TO 'em_revisao';
    """)


def downgrade():
    # volta atrás em caso de downgrade
    op.execute("""
        ALTER TYPE article_status 
        RENAME VALUE 'em_revisao' TO 'in_review';
    """)
