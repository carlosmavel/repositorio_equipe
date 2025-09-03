"""Provide auto increment for article.id on Oracle

This migration replaces the attempt to convert the ``article.id`` column into an
identity column – an operation that raises ``ORA-30673`` on populated tables –
with the more compatible ``SEQUENCE`` + ``TRIGGER`` approach.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import exc

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

        # Create sequence only if it does not already exist
        seq_exists = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM user_sequences "
                "WHERE sequence_name = 'ARTICLE_SEQ'"
            )
        ).scalar()
        if not seq_exists:
            try:
                op.execute(
                    sa.text(
                        f"CREATE SEQUENCE article_seq START WITH {start_id} INCREMENT BY 1"
                    )
                )
            except exc.DatabaseError as e:
                if "ORA-01031" not in str(e):
                    raise

        # Create trigger only if it does not already exist
        trig_exists = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM user_triggers "
                "WHERE trigger_name = 'ARTICLE_BEFORE_INSERT'"
            )
        ).scalar()
        if not trig_exists:
            try:
                op.execute(
                    sa.text(
                        """
                        CREATE OR REPLACE TRIGGER article_before_insert
                        BEFORE INSERT ON article
                        FOR EACH ROW
                        BEGIN
                          IF :new.id IS NULL THEN
                            SELECT article_seq.NEXTVAL INTO :new.id FROM dual;
                          END IF;
                        END;
                        """
                    )
                )
            except exc.DatabaseError as e:
                if "ORA-01031" not in str(e):
                    raise


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        trig_exists = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM user_triggers "
                "WHERE trigger_name = 'ARTICLE_BEFORE_INSERT'"
            )
        ).scalar()
        if trig_exists:
            op.execute(sa.text("DROP TRIGGER article_before_insert"))

        seq_exists = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM user_sequences "
                "WHERE sequence_name = 'ARTICLE_SEQ'"
            )
        ).scalar()
        if seq_exists:
            op.execute(sa.text("DROP SEQUENCE article_seq"))
