"""add explicit diagram preview state

Revision ID: f8a1b2c3d4e5
Revises: e7a9c1d3f5b7
"""

from alembic import op
import sqlalchemy as sa


revision = 'f8a1b2c3d4e5'
down_revision = 'e7a9c1d3f5b7'
branch_labels = None
depends_on = None


def upgrade():
    # Registros históricos sem raster são ausência definitiva; snapshots
    # criados pela aplicação nova passam a informar ``pending`` explicitamente.
    op.add_column('diagram_version', sa.Column(
        'preview_state', sa.String(20), nullable=False, server_default='failed',
    ))
    op.add_column('diagram_version', sa.Column('preview_error', sa.String(200), nullable=True))
    op.execute(sa.text("""
        UPDATE diagram_version SET preview_state = 'ready'
        WHERE EXISTS (
            SELECT 1 FROM diagram_version_asset dva
            JOIN diagram_asset da ON da.id = dva.asset_id
            WHERE dva.version_id = diagram_version.id AND da.kind = 'preview'
        )
    """))
    op.create_check_constraint(
        'ck_diagram_version_preview_state', 'diagram_version',
        "preview_state IN ('pending', 'generating', 'ready', 'failed')",
    )
    op.alter_column('diagram_version', 'preview_state', server_default='pending')


def downgrade():
    op.drop_constraint('ck_diagram_version_preview_state', 'diagram_version', type_='check')
    op.drop_column('diagram_version', 'preview_error')
    op.drop_column('diagram_version', 'preview_state')
