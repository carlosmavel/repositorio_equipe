"""Add review_comment column to Article

Revision ID: d3767e7caa30
Revises: d2fe50167f49
Create Date: 2025-05-16 15:52:21.344233

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3767e7caa30'
down_revision = 'd2fe50167f49'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands manually adjusted ###
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.add_column(sa.Column('review_comment', sa.TEXT(), nullable=True))
    # ### end commands ###



def downgrade() -> None:
    # ### commands manually adjusted ###
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.drop_column('review_comment')
    # ### end commands ###