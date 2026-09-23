"""version diagram save schema and assets

Revision ID: a4d5e6f7b8c9
Revises: f2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a4d5e6f7b8c9'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade():
    op.add_column('diagram', sa.Column('current_version_id', UUID, nullable=True))
    op.add_column('diagram', sa.Column('lock_version', sa.Integer(), server_default='0', nullable=False))
    op.create_foreign_key('fk_diagram_current_version_id', 'diagram', 'diagram_version',
                          ['current_version_id'], ['id'], ondelete='SET NULL', use_alter=True)

    op.add_column('diagram_version', sa.Column('schema_version', sa.Integer(), server_default='1', nullable=False))
    op.add_column('diagram_version', sa.Column('content_hash', sa.String(64), server_default='', nullable=False))
    op.add_column('diagram_asset', sa.Column('sha256', sa.String(64), server_default='', nullable=False))
    op.add_column('diagram_asset', sa.Column('byte_size', sa.BigInteger(), server_default='0', nullable=False))
    # Chaves agora representam blobs compartilháveis por conteúdo. Diagramas
    # distintos podem legitimamente apontar para a mesma chave SHA-256.
    op.drop_constraint('diagram_asset_storage_key_key', 'diagram_asset', type_='unique')

    op.create_table(
        'diagram_version_asset',
        sa.Column('version_id', UUID, sa.ForeignKey('diagram_version.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('asset_id', UUID, sa.ForeignKey('diagram_asset.id', ondelete='RESTRICT'), primary_key=True),
    )
    op.create_index('ix_diagram_version_asset_asset_id', 'diagram_version_asset', ['asset_id'])

    # Preserve the pointer for installations which already contain diagrams.
    op.execute(sa.text("""
        UPDATE diagram AS d SET current_version_id = (
          SELECT v.id FROM diagram_version AS v
          WHERE v.diagram_id = d.id AND v.version_number = d.current_version
          LIMIT 1
        )
    """))


def downgrade():
    op.drop_table('diagram_version_asset')
    op.create_unique_constraint('diagram_asset_storage_key_key', 'diagram_asset', ['storage_key'])
    op.drop_column('diagram_asset', 'byte_size')
    op.drop_column('diagram_asset', 'sha256')
    op.drop_column('diagram_version', 'content_hash')
    op.drop_column('diagram_version', 'schema_version')
    op.drop_constraint('fk_diagram_current_version_id', 'diagram', type_='foreignkey')
    op.drop_column('diagram', 'lock_version')
    op.drop_column('diagram', 'current_version_id')
