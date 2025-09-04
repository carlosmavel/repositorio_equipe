"""Ensure auto increment via sequences and triggers on Oracle

Revision ID: 8888a90cde1f
Revises: fa23b0c1c9d0
Create Date: 2025-08-30 00:00:00.000000
"""

import logging
from alembic import op
import sqlalchemy as sa
from sqlalchemy import exc

revision = '8888a90cde1f'
down_revision = ('fa23b0c1c9d0', 'c4f9b8e3d7a1')
branch_labels = None
depends_on = None


def _ensure_sequence_and_trigger(bind, table, logger):
    """Create sequence/trigger pair for a table if missing.

    ``table`` may be provided in lower case to force creation of
    objects such as ``comment_seq`` instead of ``COMMENT_seq``.
    The underlying table is always referenced using its upper-case
    identifier to avoid issues with reserved words like ``COMMENT``.
    """

    seq = f"{table}_seq"
    trig = f"{table}_before_insert"
    # Always reference the table using an upper-case quoted identifier.
    # Quoting avoids conflicts when the table name is a reserved word
    # (e.g. COMMENT, USER, ORDER).
    q_table = table.upper().replace('"', '""')
    q_table_sql = f'"{q_table}"'
    try:
        start_id = bind.execute(
            sa.text(f"SELECT NVL(MAX(id), 0) + 1 FROM {q_table_sql}")
        ).scalar()
    except exc.DatabaseError as e:
        logger.warning(
            "Skipping table %s: unable to compute MAX(id) (%s)", table, e,
            exc_info=True,
        )
        return
    try:
        # Remove any legacy default first
        bind.exec_driver_sql(
            f"ALTER TABLE {q_table_sql} MODIFY (id DEFAULT NULL)"
        )

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

        # Always (re)create the trigger so a previously broken definition
        # (e.g. missing quotes around a reserved table name) is replaced.
        try:
            bind.exec_driver_sql(
                f"""
                CREATE OR REPLACE TRIGGER {trig}
                BEFORE INSERT ON {q_table_sql}
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
    except exc.DatabaseError as e:
        logger.warning("Skipping table %s: %s", table, e, exc_info=True)
        return


logger = logging.getLogger("alembic.runtime.migration")


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        reserved_tables = {"comment", "user", "order"}
        # Ensure reserved-word tables get handled explicitly using lowercase
        for rtable in reserved_tables:
            _ensure_sequence_and_trigger(bind, rtable, logger)

        numeric_tables = bind.execute(
            sa.text(
                "SELECT table_name FROM user_tab_columns "
                "WHERE column_name = 'ID' AND identity_column = 'NO' "
                "AND data_type = 'NUMBER'"
            )
        ).scalars().all()
        skipped = bind.execute(
            sa.text(
                "SELECT table_name, data_type FROM user_tab_columns "
                "WHERE column_name = 'ID' AND identity_column = 'NO' "
                "AND data_type <> 'NUMBER'"
            )
        ).fetchall()
        for table, data_type in skipped:
            logger.info(
                "Skipping table %s: ID column type %s is not numeric", table, data_type
            )
        for table in numeric_tables:
            if table.lower() in reserved_tables:
                # Already handled explicitly above
                continue
            if table != table.upper():
                logger.info(
                    "Table %s has case-sensitive name; using quoted identifiers",
                    table,
                )
            _ensure_sequence_and_trigger(bind, table, logger)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'oracle':
        reserved_tables = {"comment", "user", "order"}
        # Drop explicitly created objects for reserved-word tables
        for rtable in reserved_tables:
            trig = f"{rtable}_before_insert"
            seq = f"{rtable}_seq"
            trig_exists = bind.execute(
                sa.text(
                    "SELECT COUNT(*) FROM user_triggers "
                    "WHERE trigger_name = :name"
                ),
                {"name": trig.upper()},
            ).scalar()
            if trig_exists:
                bind.exec_driver_sql(f"DROP TRIGGER {trig}")

            seq_exists = bind.execute(
                sa.text(
                    "SELECT COUNT(*) FROM user_sequences "
                    "WHERE sequence_name = :name"
                ),
                {"name": seq.upper()},
            ).scalar()
            if seq_exists:
                bind.exec_driver_sql(f"DROP SEQUENCE {seq}")

        numeric_tables = bind.execute(
            sa.text(
                "SELECT table_name FROM user_tab_columns "
                "WHERE column_name = 'ID' AND identity_column = 'NO' "
                "AND data_type = 'NUMBER'"
            )
        ).scalars().all()
        skipped = bind.execute(
            sa.text(
                "SELECT table_name, data_type FROM user_tab_columns "
                "WHERE column_name = 'ID' AND identity_column = 'NO' "
                "AND data_type <> 'NUMBER'"
            )
        ).fetchall()
        for table, data_type in skipped:
            logger.info(
                "Skipping table %s: ID column type %s is not numeric", table, data_type
            )
        for table in numeric_tables:
            if table.lower() in reserved_tables:
                # Reserved tables handled explicitly above
                continue
            if table != table.upper():
                logger.info(
                    "Table %s has case-sensitive name; using quoted identifiers",
                    table,
                )
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
