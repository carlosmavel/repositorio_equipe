"""convert article.id to identity for auto increment"""

from alembic import op
import sqlalchemy as sa

revision = 'c4f9b8e3d7a1'
down_revision = ('bb1d9e24176f', '0b1c2d3e4f67')
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        start_id = bind.execute(
            sa.text("SELECT NVL(MAX(id), 0) + 1 FROM article")
        ).scalar()
        # Remove legacy default that referenced a sequence
        op.execute(sa.text("ALTER TABLE article MODIFY (id DEFAULT NULL)"))

        # First convert the column into an identity. Using "GENERATED AS
        # IDENTITY" avoids ORA-30673 when changing a populated column that was
        # previously filled via a sequence or trigger.
        op.execute(sa.text("ALTER TABLE article MODIFY (id GENERATED AS IDENTITY)"))

        # Restart the identity sequence so that it continues after existing
        # rows. This requires the column to already be an identity, so the
        # previous statement must succeed before this runs.
        op.execute(
            sa.text(
                f"ALTER TABLE article MODIFY (id RESTART START WITH {start_id})"
            )
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        op.execute(
            sa.text("ALTER TABLE article MODIFY (id DROP IDENTITY)")
        )
