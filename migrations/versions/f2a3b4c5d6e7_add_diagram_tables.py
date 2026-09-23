"""add diagram tables

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'diagram',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('celula_id', sa.Integer(), sa.ForeignKey('celula.id'), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'diagram_version',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('diagram_id', sa.Integer(), sa.ForeignKey('diagram.id', ondelete='CASCADE'), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('diagram_id', 'number', name='uq_diagram_version_number'),
    )
    op.create_table(
        'diagram_asset',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('diagram_id', sa.Integer(), sa.ForeignKey('diagram.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=False, unique=True),
        sa.Column('kind', sa.String(32), server_default='asset', nullable=False),
        sa.Column('content_type', sa.String(120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'article_diagram',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('article.id', ondelete='CASCADE'), nullable=False),
        sa.Column('diagram_id', sa.Integer(), sa.ForeignKey('diagram.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('article_id', 'diagram_id', name='uq_article_diagram'),
    )


def downgrade():
    op.drop_table('article_diagram')
    op.drop_table('diagram_asset')
    op.drop_table('diagram_version')
    op.drop_table('diagram')
