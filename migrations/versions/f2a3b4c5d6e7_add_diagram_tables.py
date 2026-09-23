"""add diagram domain tables

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _fk(column, target, ondelete):
    return sa.ForeignKey(column, name=target, ondelete=ondelete)


def upgrade():
    op.create_table(
        'diagram',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('scene_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('owner_id', sa.Integer(), _fk('user.id', 'fk_diagram_owner_id_user', 'RESTRICT'), nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('diagram_type', sa.String(20), server_default='diagram', nullable=False),
        sa.Column('scope', sa.String(20), server_default='private', nullable=False),
        sa.Column('instituicao_id', sa.Integer(), _fk('instituicao.id', 'fk_diagram_instituicao_id', 'RESTRICT')),
        sa.Column('estabelecimento_id', sa.Integer(), _fk('estabelecimento.id', 'fk_diagram_estabelecimento_id', 'RESTRICT')),
        sa.Column('setor_id', sa.Integer(), _fk('setor.id', 'fk_diagram_setor_id', 'RESTRICT')),
        sa.Column('celula_id', sa.Integer(), _fk('celula.id', 'fk_diagram_celula_id', 'RESTRICT')),
        sa.Column('source_diagram_id', UUID, _fk('diagram.id', 'fk_diagram_source_diagram_id', 'SET NULL')),
        sa.Column('archived_at', sa.DateTime(timezone=True)),
        sa.Column('current_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name='ck_diagram_status'),
        sa.CheckConstraint("diagram_type IN ('diagram', 'template')", name='ck_diagram_type'),
        sa.CheckConstraint("scope IN ('private', 'institution', 'establishment', 'sector', 'cell')", name='ck_diagram_scope'),
        sa.CheckConstraint('current_version > 0', name='ck_diagram_current_version_positive'),
    )
    for name, columns in (
        ('ix_diagram_owner_id', ['owner_id']), ('ix_diagram_status', ['status']),
        ('ix_diagram_type', ['diagram_type']), ('ix_diagram_scope', ['scope']),
        ('ix_diagram_updated_at', ['updated_at']), ('ix_diagram_name', ['name']),
        ('ix_diagram_instituicao_id', ['instituicao_id']),
        ('ix_diagram_estabelecimento_id', ['estabelecimento_id']),
        ('ix_diagram_setor_id', ['setor_id']), ('ix_diagram_celula_id', ['celula_id']),
    ):
        op.create_index(name, 'diagram', columns)

    op.create_table(
        'diagram_version',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('diagram_id', UUID, _fk('diagram.id', 'fk_diagram_version_diagram_id', 'CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('scene_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('author_id', sa.Integer(), _fk('user.id', 'fk_diagram_version_author_id', 'RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('version_number > 0', name='ck_diagram_version_number_positive'),
        sa.UniqueConstraint('diagram_id', 'version_number', name='uq_diagram_version_number'),
    )
    op.create_index('ix_diagram_version_diagram_id', 'diagram_version', ['diagram_id'])

    op.create_table(
        'diagram_asset',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('diagram_id', UUID, _fk('diagram.id', 'fk_diagram_asset_diagram_id', 'CASCADE'), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=False, unique=True),
        sa.Column('kind', sa.String(32), server_default='asset', nullable=False),
        sa.Column('content_type', sa.String(120)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_diagram_asset_diagram_id', 'diagram_asset', ['diagram_id'])

    op.create_table(
        'article_diagram',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('article_id', sa.Integer(), _fk('article.id', 'fk_article_diagram_article_id', 'CASCADE'), nullable=False),
        sa.Column('diagram_id', UUID, _fk('diagram.id', 'fk_article_diagram_diagram_id', 'RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('article_id', 'diagram_id', name='uq_article_diagram'),
    )
    op.create_index('ix_article_diagram_diagram_id', 'article_diagram', ['diagram_id'])

    # Explicit ACL tables supplement the primary organizational scope. Their
    # composite PK also prevents duplicate grants.
    for suffix, target in (
        ('user', 'user.id'), ('instituicao', 'instituicao.id'),
        ('estabelecimento', 'estabelecimento.id'), ('setor', 'setor.id'),
        ('celula', 'celula.id'),
    ):
        target_column = f'{suffix}_id'
        table = f'diagram_share_{suffix}'
        op.create_table(
            table,
            sa.Column('diagram_id', UUID, _fk('diagram.id', f'fk_{table}_diagram_id', 'CASCADE'), primary_key=True),
            sa.Column(target_column, sa.Integer(), _fk(target, f'fk_{table}_{target_column}', 'CASCADE'), primary_key=True),
        )
        op.create_index(f'ix_{table}_{target_column}', table, [target_column])


def downgrade():
    for suffix in ('celula', 'setor', 'estabelecimento', 'instituicao', 'user'):
        op.drop_table(f'diagram_share_{suffix}')
    op.drop_table('article_diagram')
    op.drop_table('diagram_asset')
    op.drop_table('diagram_version')
    op.drop_table('diagram')
