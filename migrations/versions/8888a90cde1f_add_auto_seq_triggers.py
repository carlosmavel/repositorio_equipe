"""Ensure auto increment via sequences and triggers on Oracle

Revision ID: 8888a90cde1f
Revises: fa23b0c1c9d0
Create Date: 2025-08-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import exc

revision = '8888a90cde1f'
down_revision = ('fa23b0c1c9d0', 'c4f9b8e3d7a1')
branch_labels = None
depends_on = None


def _ensure_sequence_and_trigger(bind, table):
    seq = f"{table}_seq"
    trig = f"{table}_before_insert"
    start_id = bind.execute(
        sa.text(f"SELECT NVL(MAX(id), 0) + 1 FROM {table}")
    ).scalar()
    # Remove any legacy default first
    bind.exec_driver_sql(f"ALTER TABLE {table} MODIFY (id DEFAULT NULL)")

    seq_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM user_sequences WHERE sequence_name = :name"
        ),
        {"name": seq.upper()},
    ).scalar()
    if not seq_exists:
        try:
            bind.exec_driver_sql(
                f"CREATE SEQUENCE {seq} START WITH {start_id} INCREMENT BY 1"
            )
        except exc.DatabaseError as e:
            if "ORA-01031" not in str(e):
                raise

    trig_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM user_triggers WHERE trigger_name = :name"
        ),
        {"name": trig.upper()},
    ).scalar()
    if not trig_exists:
        try:
            bind.exec_driver_sql(
                f"""
                CREATE OR REPLACE TRIGGER {trig}
                BEFORE INSERT ON {table}
                FOR EACH ROW
                BEGIN
                  IF :new.id IS NULL THEN
                    SELECT {seq}.NEXTVAL INTO :new.id FROM dual;
                  END IF;
                END;
                """
            )
        except exc.DatabaseError as e:
            if "ORA-01031" not in str(e):
                raise


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        tables = bind.execute(
            sa.text(
                "SELECT table_name FROM user_tab_columns "
                "WHERE column_name = 'ID' AND identity_column = 'NO'"
            )
        ).scalars().all()
        for table in tables:
            _ensure_sequence_and_trigger(bind, table)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        tables = bind.execute(
            sa.text(
                "SELECT table_name FROM user_tab_columns "
                "WHERE column_name = 'ID' AND identity_column = 'NO'"
            )
        ).scalars().all()
        for table in tables:
            seq = f"{table}_seq"
            trig = f"{table}_before_insert"
            trig_exists = bind.execute(
                sa.text(
                    "SELECT COUNT(*) FROM user_triggers WHERE trigger_name = :name"
                ),
                {"name": trig.upper()},
            ).scalar()
            if trig_exists:
                bind.exec_driver_sql(f"DROP TRIGGER {trig}")

            seq_exists = bind.execute(
                sa.text(
                    "SELECT COUNT(*) FROM user_sequences WHERE sequence_name = :name"
                ),
                {"name": seq.upper()},
            ).scalar()
            if seq_exists:
                bind.exec_driver_sql(f"DROP SEQUENCE {seq}")
