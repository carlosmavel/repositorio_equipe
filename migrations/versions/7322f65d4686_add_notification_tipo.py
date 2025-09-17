"""add notification tipo

Revision ID: 7322f65d4686
Revises: bb1d9e24176f
Create Date: 2025-08-01 17:15:20.814777

"""
from alembic import op
import sqlalchemy as sa


def _has_column(table_name: str, column_name: str) -> bool:
    """Return True if the given column exists in the given table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    return column_name in cols


# revision identifiers, used by Alembic.
revision = '7322f65d4686'
down_revision = 'bb1d9e24176f'
branch_labels = None
depends_on = None


def upgrade():
    """Add 'tipo' column to notification if it doesn't exist."""
    if not _has_column("notification", "tipo"):
        with op.batch_alter_table("notification") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "tipo",
                    sa.String(length=20),
                    nullable=False,
                    server_default="geral",
                )
            )


def downgrade():
    """Remove 'tipo' column from notification if present."""
    if _has_column("notification", "tipo"):
        with op.batch_alter_table("notification") as batch_op:
            batch_op.drop_column("tipo")
