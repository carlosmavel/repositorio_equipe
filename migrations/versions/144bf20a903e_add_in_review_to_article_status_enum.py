"""Add in_review to article_status enum

Revision ID: 144bf20a903e
Revises: cccfd9ae08b3
Create Date: 2025-05-20 16:46:30.259567

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '144bf20a903e'
down_revision = 'cccfd9ae08b3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE article_status ADD VALUE 'in_review';")


def downgrade():
    pass
