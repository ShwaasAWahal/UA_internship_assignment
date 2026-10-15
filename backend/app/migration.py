import logging
from sqlalchemy import Engine, text
from app.database import Base

logger = logging.getLogger(__name__)

# Complete required set of named constraints for issues table
REQUIRED_ISSUES_CONSTRAINTS: frozenset[str] = frozenset({
    "ck_issues_severity",
    "ck_issues_status",
    "ck_issues_version",
    "ck_issues_title_not_blank",
})

# Complete required set of named constraints for issue_status_history table
REQUIRED_HISTORY_CONSTRAINTS: frozenset[str] = frozenset({
    "ck_history_previous_status",
    "ck_history_new_status",
})


def migrate_sqlite_schema(engine: Engine) -> bool:
    """Safely migrate SQLite database schema to add all required check constraints non-destructively.

    Follows SQLite's 12-step table recreation guidelines.
    Existing rows, primary keys, foreign keys, and indexes are completely preserved.
    Returns True if a migration rebuild was performed, False if the schema is already current.
    """
    if engine.dialect.name != "sqlite":
        return False

    with engine.connect() as conn:
        res_issues = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='issues'")
        ).fetchone()
        issues_sql = res_issues[0] if (res_issues and res_issues[0]) else ""

        res_history = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='issue_status_history'")
        ).fetchone()
        history_sql = res_history[0] if (res_history and res_history[0]) else ""

        # Skip migration only when EVERY required constraint is present
        need_issues_migration = bool(
            issues_sql and any(c not in issues_sql for c in REQUIRED_ISSUES_CONSTRAINTS)
        )
        need_history_migration = bool(
            history_sql and any(c not in history_sql for c in REQUIRED_HISTORY_CONSTRAINTS)
        )

        if not need_issues_migration and not need_history_migration:
            logger.debug("Database schema is fully compliant. No rebuild needed.")
            return False

    logger.info(
        "Migrating SQLite schema to add missing CheckConstraints (issues=%s, history=%s)...",
        need_issues_migration,
        need_history_migration,
    )

    with engine.connect() as conn:
        # Access underlying DBAPI connection to manage SQLite connection-scoped pragmas safely
        raw_conn = conn.connection.dbapi_connection
        raw_conn.execute("PRAGMA foreign_keys = OFF;")
        raw_conn.execute("PRAGMA legacy_alter_table = ON;")

        trans = conn.begin()
        try:
            if need_issues_migration:
                conn.execute(text("DROP TABLE IF EXISTS _issues_old_migration;"))
                conn.execute(text("ALTER TABLE issues RENAME TO _issues_old_migration;"))

                # Drop old indexes so their names can be cleanly created on the new table
                old_indexes = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='_issues_old_migration' AND name NOT LIKE 'sqlite_autoindex%'"
                )).fetchall()
                for idx in old_indexes:
                    conn.execute(text(f'DROP INDEX IF EXISTS "{idx[0]}";'))

                # Re-create table with all CheckConstraints and new indexes
                Base.metadata.tables["issues"].create(bind=conn)

                # Copy all existing data
                conn.execute(text("""
                    INSERT INTO issues (
                        id, owner_id, title, description, page_url, 
                        wcag_criterion, severity, status, version, 
                        created_at, updated_at
                    )
                    SELECT 
                        id, owner_id, title, description, page_url, 
                        wcag_criterion, severity, status, version, 
                        created_at, updated_at 
                    FROM _issues_old_migration;
                """))
                conn.execute(text("DROP TABLE _issues_old_migration;"))

            if need_history_migration:
                conn.execute(text("DROP TABLE IF EXISTS _history_old_migration;"))
                conn.execute(text("ALTER TABLE issue_status_history RENAME TO _history_old_migration;"))

                # Drop old history indexes
                old_hist_indexes = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='_history_old_migration' AND name NOT LIKE 'sqlite_autoindex%'"
                )).fetchall()
                for idx in old_hist_indexes:
                    conn.execute(text(f'DROP INDEX IF EXISTS "{idx[0]}";'))

                # Re-create history table with all CheckConstraints
                Base.metadata.tables["issue_status_history"].create(bind=conn)

                # Copy all existing data
                conn.execute(text("""
                    INSERT INTO issue_status_history (
                        id, issue_id, actor_id, previous_status, 
                        new_status, changed_at, comment
                    )
                    SELECT 
                        id, issue_id, actor_id, previous_status, 
                        new_status, changed_at, comment 
                    FROM _history_old_migration;
                """))
                conn.execute(text("DROP TABLE _history_old_migration;"))

            # Verify foreign key integrity
            fk_violations = conn.execute(text("PRAGMA foreign_key_check;")).fetchall()
            if fk_violations:
                raise RuntimeError(f"Foreign key violations detected during table migration: {fk_violations}")

            trans.commit()
            logger.info("SQLite schema migration completed successfully.")
        except Exception as exc:
            trans.rollback()
            logger.error("Failed to migrate SQLite schema: %s", exc, exc_info=True)
            raise
        finally:
            raw_conn.execute("PRAGMA legacy_alter_table = OFF;")
            raw_conn.execute("PRAGMA foreign_keys = ON;")

    return True
