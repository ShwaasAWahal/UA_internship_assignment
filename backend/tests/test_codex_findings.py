import hashlib
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud
from app.config import settings
from app.database import Base
from app.migration import migrate_sqlite_schema
from app.models import Issue, IssueStatusHistory, SeverityEnum, StatusEnum, User
from app.schemas import IssueCreate, IssueStatusUpdate, IssueUpdate
from app.seed import init_db_and_seed


# ---------------------------------------------------------------------------
# Finding 1: Health endpoint leaks database exception details
# ---------------------------------------------------------------------------

def test_health_check_failure_hides_internal_exception_details(client):
    """Verify health failure returns generic DATABASE_UNAVAILABLE without leaking internal paths or SQL details."""
    sensitive_db_path = "C:/private/internal/cluster/credentials_and_secrets/db.sqlite"
    simulated_error = sqlite3.OperationalError(f"unable to open database file at {sensitive_db_path}")

    with patch("sqlalchemy.orm.Session.execute", side_effect=simulated_error):
        # Test /health
        res = client.get("/health")
        assert res.status_code == 503
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert data["error"]["message"] == "Database service is currently unavailable."

        # Verify sensitive info is NOT leaked anywhere in the response body or text
        response_text = res.text
        assert sensitive_db_path not in response_text
        assert "OperationalError" not in response_text
        assert "credentials_and_secrets" not in response_text

        # Test /api/health as well
        res_api = client.get("/api/health")
        assert res_api.status_code == 503
        assert res_api.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert sensitive_db_path not in res_api.text


# ---------------------------------------------------------------------------
# Finding 2: Missing database CHECK constraints & safe migration
# ---------------------------------------------------------------------------

def test_database_check_constraint_rejects_invalid_severity(db_session):
    """Verify that direct database insert with invalid severity violates ck_issues_severity."""
    invalid_issue = Issue(
        owner_id="demo-user-alice",
        title="Check severity test",
        page_url="https://example.com",
        severity="NonExistentSeverity",
        status="Open",
        version=1,
    )
    db_session.add(invalid_issue)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert "CHECK constraint failed" in str(exc_info.value) or "ck_issues_severity" in str(exc_info.value)


def test_database_check_constraint_rejects_invalid_status(db_session):
    """Verify that direct database insert with invalid status violates ck_issues_status."""
    invalid_issue = Issue(
        owner_id="demo-user-alice",
        title="Check status test",
        page_url="https://example.com",
        severity="Minor",
        status="InvalidStatus",
        version=1,
    )
    db_session.add(invalid_issue)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert "CHECK constraint failed" in str(exc_info.value) or "ck_issues_status" in str(exc_info.value)


def test_database_check_constraint_rejects_version_less_than_one(db_session):
    """Verify that direct database insert with version < 1 violates ck_issues_version."""
    invalid_issue = Issue(
        owner_id="demo-user-alice",
        title="Check version test",
        page_url="https://example.com",
        severity="Minor",
        status="Open",
        version=0,
    )
    db_session.add(invalid_issue)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert "CHECK constraint failed" in str(exc_info.value) or "ck_issues_version" in str(exc_info.value)


def test_database_check_constraint_rejects_blank_or_whitespace_title(db_session):
    """Verify that direct database insert with empty/whitespace title violates ck_issues_title_not_blank."""
    invalid_issue = Issue(
        owner_id="demo-user-alice",
        title="    ",
        page_url="https://example.com",
        severity="Minor",
        status="Open",
        version=1,
    )
    db_session.add(invalid_issue)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert "CHECK constraint failed" in str(exc_info.value) or "ck_issues_title_not_blank" in str(exc_info.value)


def test_migration_partially_migrated_issues_table_rebuilds_and_enforces_missing_constraints():
    """Verify that an issues table containing severity and title constraints but lacking status and version constraints is rebuilt."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE users (
                id VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                team_id VARCHAR(64),
                created_at DATETIME NOT NULL
            );
        """)
        # Issues table with ONLY severity and title constraints, missing status and version constraints
        conn.execute("""
            CREATE TABLE issues (
                id INTEGER PRIMARY KEY,
                owner_id VARCHAR(64) NOT NULL REFERENCES users(id),
                title VARCHAR(255) NOT NULL,
                description TEXT,
                page_url VARCHAR(2048) NOT NULL,
                wcag_criterion VARCHAR(100),
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL,
                version INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT ck_issues_severity CHECK (severity IN ('Minor', 'Moderate', 'Serious', 'Critical')),
                CONSTRAINT ck_issues_title_not_blank CHECK (length(trim(title)) > 0)
            );
        """)
        conn.execute("""
            CREATE TABLE issue_status_history (
                id INTEGER PRIMARY KEY,
                issue_id INTEGER NOT NULL REFERENCES issues(id),
                actor_id VARCHAR(64) NOT NULL REFERENCES users(id),
                previous_status VARCHAR(20) NOT NULL,
                new_status VARCHAR(20) NOT NULL,
                changed_at DATETIME NOT NULL,
                comment TEXT,
                CONSTRAINT ck_history_previous_status CHECK (previous_status IN ('Open', 'In Progress', 'Resolved')),
                CONSTRAINT ck_history_new_status CHECK (new_status IN ('Open', 'In Progress', 'Resolved'))
            );
        """)
        conn.execute("INSERT INTO users VALUES ('user-partial', 'partial@example.com', 'Partial Auditor', 'auditor', NULL, '2026-01-01');")
        conn.execute("INSERT INTO issues VALUES (20, 'user-partial', 'Partial Issue', NULL, 'https://example.com/p', NULL, 'Serious', 'Open', 1, '2026-01-01', '2026-01-01');")
        conn.execute("INSERT INTO issue_status_history VALUES (200, 20, 'user-partial', 'Open', 'In Progress', '2026-01-01', 'Initial audit');")
        conn.commit()
        conn.close()

        engine = create_engine(f"sqlite:///{db_path}")
        rebuilt = migrate_sqlite_schema(engine)
        assert rebuilt is True, "Migration must rebuild table when status or version constraints are missing."

        # Directly inspect schema using SQLite
        conn_check = sqlite3.connect(db_path)
        schema_sql = conn_check.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issues'").fetchone()[0]
        assert "ck_issues_severity" in schema_sql
        assert "ck_issues_title_not_blank" in schema_sql
        assert "ck_issues_status" in schema_sql, "Missing ck_issues_status after migration"
        assert "ck_issues_version" in schema_sql, "Missing ck_issues_version after migration"

        # Verify existing data preserved
        issue = conn_check.execute("SELECT id, owner_id, title, severity FROM issues WHERE id = 20").fetchone()
        assert issue == (20, "user-partial", "Partial Issue", "Serious")
        history = conn_check.execute("SELECT id, issue_id, new_status FROM issue_status_history WHERE id = 200").fetchone()
        assert history == (200, 20, "In Progress")

        # Verify that newly added constraints actively reject invalid status & version
        with pytest.raises(sqlite3.IntegrityError):
            conn_check.execute("INSERT INTO issues VALUES (21, 'user-partial', 'Bad Status', NULL, 'https://example.com', NULL, 'Minor', 'UnknownStatus', 1, '2026-01-01', '2026-01-01');")

        with pytest.raises(sqlite3.IntegrityError):
            conn_check.execute("INSERT INTO issues VALUES (22, 'user-partial', 'Bad Version', NULL, 'https://example.com', NULL, 'Minor', 'Open', 0, '2026-01-01', '2026-01-01');")

        # Foreign key integrity check
        fk_violations = conn_check.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(fk_violations) == 0, f"FK check failed: {fk_violations}"

        conn_check.close()
        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_migration_partially_migrated_history_table_rebuilds_and_enforces_missing_constraints():
    """Verify that a history table lacking its expected new-status constraint is rebuilt."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE users (
                id VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                team_id VARCHAR(64),
                created_at DATETIME NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE issues (
                id INTEGER PRIMARY KEY,
                owner_id VARCHAR(64) NOT NULL REFERENCES users(id),
                title VARCHAR(255) NOT NULL,
                description TEXT,
                page_url VARCHAR(2048) NOT NULL,
                wcag_criterion VARCHAR(100),
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL,
                version INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT ck_issues_severity CHECK (severity IN ('Minor', 'Moderate', 'Serious', 'Critical')),
                CONSTRAINT ck_issues_status CHECK (status IN ('Open', 'In Progress', 'Resolved')),
                CONSTRAINT ck_issues_version CHECK (version >= 1),
                CONSTRAINT ck_issues_title_not_blank CHECK (length(trim(title)) > 0)
            );
        """)
        # History table lacking ck_history_new_status constraint
        conn.execute("""
            CREATE TABLE issue_status_history (
                id INTEGER PRIMARY KEY,
                issue_id INTEGER NOT NULL REFERENCES issues(id),
                actor_id VARCHAR(64) NOT NULL REFERENCES users(id),
                previous_status VARCHAR(20) NOT NULL,
                new_status VARCHAR(20) NOT NULL,
                changed_at DATETIME NOT NULL,
                comment TEXT,
                CONSTRAINT ck_history_previous_status CHECK (previous_status IN ('Open', 'In Progress', 'Resolved'))
            );
        """)
        conn.execute("INSERT INTO users VALUES ('user-hist', 'hist@example.com', 'Hist Auditor', 'auditor', NULL, '2026-01-01');")
        conn.execute("INSERT INTO issues VALUES (30, 'user-hist', 'Hist Issue', NULL, 'https://example.com/h', NULL, 'Minor', 'Open', 1, '2026-01-01', '2026-01-01');")
        conn.execute("INSERT INTO issue_status_history VALUES (300, 30, 'user-hist', 'Open', 'In Progress', '2026-01-01', 'Note');")
        conn.commit()
        conn.close()

        engine = create_engine(f"sqlite:///{db_path}")
        rebuilt = migrate_sqlite_schema(engine)
        assert rebuilt is True, "Migration must rebuild history table when new_status constraint is missing."

        conn_check = sqlite3.connect(db_path)
        schema_hist = conn_check.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issue_status_history'").fetchone()[0]
        assert "ck_history_previous_status" in schema_hist
        assert "ck_history_new_status" in schema_hist

        # Existing history row preserved
        row = conn_check.execute("SELECT id, issue_id, new_status FROM issue_status_history WHERE id = 300").fetchone()
        assert row == (300, 30, "In Progress")

        # Verify that invalid new_status is rejected
        with pytest.raises(sqlite3.IntegrityError):
            conn_check.execute("INSERT INTO issue_status_history VALUES (301, 30, 'user-hist', 'Open', 'InvalidNextStatus', '2026-01-01', NULL);")

        conn_check.close()
        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_migration_fully_migrated_database_skips_unnecessary_rebuild():
    """Verify that a fully compliant database skips rebuild without modifying tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        # Build schema using metadata (has all CheckConstraints)
        Base.metadata.create_all(bind=engine)

        conn = sqlite3.connect(db_path)
        issues_sql_before = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issues'").fetchone()[0]
        history_sql_before = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issue_status_history'").fetchone()[0]
        conn.close()

        # Running migration on current schema must return False (no rebuild)
        rebuilt = migrate_sqlite_schema(engine)
        assert rebuilt is False, "migrate_sqlite_schema must return False when schema is already current."

        # Verify schema is completely untouched
        conn = sqlite3.connect(db_path)
        issues_sql_after = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issues'").fetchone()[0]
        history_sql_after = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issue_status_history'").fetchone()[0]
        conn.close()

        assert issues_sql_before == issues_sql_after
        assert history_sql_before == history_sql_after

        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_migration_preserves_valid_existing_data():
    """Verify that migrate_sqlite_schema adds constraints to an unconstrained legacy SQLite DB without losing data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create unconstrained legacy schema manually
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE users (
                id VARCHAR(64) NOT NULL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                team_id VARCHAR(64),
                created_at DATETIME NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE issues (
                id INTEGER NOT NULL PRIMARY KEY,
                owner_id VARCHAR(64) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                page_url VARCHAR(2048) NOT NULL,
                wcag_criterion VARCHAR(100),
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL,
                version INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(owner_id) REFERENCES users (id)
            );
        """)
        conn.execute("""
            CREATE TABLE issue_status_history (
                id INTEGER NOT NULL PRIMARY KEY,
                issue_id INTEGER NOT NULL,
                actor_id VARCHAR(64) NOT NULL,
                previous_status VARCHAR(20) NOT NULL,
                new_status VARCHAR(20) NOT NULL,
                changed_at DATETIME NOT NULL,
                comment TEXT,
                FOREIGN KEY(issue_id) REFERENCES issues (id),
                FOREIGN KEY(actor_id) REFERENCES users (id)
            );
        """)
        conn.execute("""
            INSERT INTO users (id, email, display_name, role, created_at)
            VALUES ('legacy-user-1', 'legacy@example.com', 'Legacy Auditor', 'auditor', '2026-01-01 00:00:00');
        """)
        conn.execute("""
            INSERT INTO issues (id, owner_id, title, page_url, severity, status, version, created_at, updated_at)
            VALUES (99, 'legacy-user-1', 'Existing Legacy Issue', 'https://example.com/legacy', 'Serious', 'Open', 1, '2026-01-01 00:00:00', '2026-01-01 00:00:00');
        """)
        conn.execute("""
            INSERT INTO issue_status_history (id, issue_id, actor_id, previous_status, new_status, changed_at, comment)
            VALUES (990, 99, 'legacy-user-1', 'Open', 'In Progress', '2026-01-01 00:00:00', 'Legacy log');
        """)
        conn.commit()
        conn.close()

        # Connect with SQLAlchemy and run migration
        engine = create_engine(f"sqlite:///{db_path}")
        rebuilt = migrate_sqlite_schema(engine)
        assert rebuilt is True

        # Verify that schema now contains CheckConstraints
        conn_check = sqlite3.connect(db_path)
        schema_sql = conn_check.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='issues'").fetchone()[0]
        assert "ck_issues_severity" in schema_sql
        assert "ck_issues_status" in schema_sql
        assert "ck_issues_version" in schema_sql
        assert "ck_issues_title_not_blank" in schema_sql

        # Verify existing data is completely intact
        row = conn_check.execute("SELECT id, owner_id, title, severity FROM issues WHERE id = 99").fetchone()
        assert row is not None
        assert row[0] == 99
        assert row[1] == "legacy-user-1"
        assert row[2] == "Existing Legacy Issue"
        assert row[3] == "Serious"

        hist_row = conn_check.execute("SELECT id, issue_id, actor_id, new_status FROM issue_status_history WHERE id = 990").fetchone()
        assert hist_row == (990, 99, "legacy-user-1", "In Progress")

        conn_check.close()
        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


# ---------------------------------------------------------------------------
# Finding 3: Tests must not create, modify, or seed backend/issues.db
# ---------------------------------------------------------------------------

def test_test_client_does_not_modify_production_db(client):
    """Verify that running TestClient requests does not create or alter the production issues.db file."""
    # Find issues.db path
    db_file = None
    if settings.DATABASE_URL.startswith("sqlite:///"):
        candidate = settings.DATABASE_URL.replace("sqlite:///", "")
        if os.path.exists(candidate):
            db_file = candidate

    if db_file:
        def get_file_hash(path: str) -> str:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        hash_before = get_file_hash(db_file)
        mtime_before = os.path.getmtime(db_file)

        # Perform multiple API operations on TestClient
        res_create = client.post(
            "/api/issues",
            json={"title": "Test isolation check", "page_url": "https://example.com/iso", "severity": "Minor"},
            headers={"X-Demo-User-Id": "demo-user-alice"},
        )
        assert res_create.status_code == 201

        res_list = client.get("/api/issues", headers={"X-Demo-User-Id": "demo-user-alice"})
        assert res_list.status_code == 200

        res_health = client.get("/health")
        assert res_health.status_code == 200

        hash_after = get_file_hash(db_file)
        mtime_after = os.path.getmtime(db_file)

        assert hash_before == hash_after, "Production database file was modified during test execution!"
        assert mtime_before == mtime_after, "Production database file mtime changed during test execution!"


# ---------------------------------------------------------------------------
# Additional Gap 1: Concurrent updates rejection
# ---------------------------------------------------------------------------

def test_concurrent_updates_independent_writers_cannot_both_succeed(client):
    """Verify that two independent writers updating the same issue version cannot both succeed silently."""
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}

    # Create initial issue at version 1
    res = client.post(
        "/api/issues",
        json={"title": "Initial Title", "page_url": "https://example.com", "severity": "Minor"},
        headers=alice_headers,
    )
    issue_id = res.json()["id"]
    assert res.json()["version"] == 1

    # Writer 1 updates version 1 -> succeeds, increments to version 2
    res_w1 = client.patch(
        f"/api/issues/{issue_id}",
        json={"title": "Writer 1 Title", "version": 1},
        headers=alice_headers,
    )
    assert res_w1.status_code == 200
    assert res_w1.json()["version"] == 2
    assert res_w1.json()["title"] == "Writer 1 Title"

    # Writer 2 attempts update based on stale version 1 -> must fail with 409 Conflict
    res_w2 = client.patch(
        f"/api/issues/{issue_id}",
        json={"title": "Writer 2 Title", "version": 1},
        headers=alice_headers,
    )
    assert res_w2.status_code == 409
    assert res_w2.json()["error"]["code"] == "CONCURRENCY_CONFLICT"

    # Final state in DB must remain Writer 1's title and version 2
    res_final = client.get(f"/api/issues/{issue_id}", headers=alice_headers)
    assert res_final.json()["version"] == 2
    assert res_final.json()["title"] == "Writer 1 Title"


# ---------------------------------------------------------------------------
# Additional Gap 2: Transaction rollback on status transition failure
# ---------------------------------------------------------------------------

def test_atomic_transaction_rollback_on_history_failure(db_session):
    """Simulate a status history write failure and verify that issue status and version remain unchanged."""
    alice = db_session.query(User).filter_by(id="demo-user-alice").first()
    issue = crud.create_issue(
        db_session,
        owner_id=alice.id,
        data=IssueCreate(
            title="Rollback test issue",
            page_url="https://example.com/rollback",
            severity=SeverityEnum.MODERATE,
        ),
    )
    initial_version = issue.version
    initial_status = issue.status
    assert initial_status == "Open"
    assert initial_version == 1

    # Simulate database failure during history entry insertion by setting an invalid new_status on history
    update_data = IssueStatusUpdate(status=StatusEnum.IN_PROGRESS, version=1, comment="Attempted transition")

    # Patch db_session.add to simulate failure when adding IssueStatusHistory
    original_add = db_session.add

    def failing_add(instance):
        if isinstance(instance, IssueStatusHistory):
            raise sqlite3.OperationalError("Simulated disk error during history logging")
        return original_add(instance)

    with patch.object(db_session, "add", side_effect=failing_add):
        with pytest.raises(sqlite3.OperationalError):
            crud.transition_issue_status(
                db=db_session,
                issue_id=issue.id,
                owner_id=alice.id,
                actor_id=alice.id,
                data=update_data,
            )

    # Roll back session
    db_session.rollback()

    # Query fresh issue from database
    refreshed_issue = db_session.query(Issue).filter_by(id=issue.id).first()
    assert refreshed_issue.status == "Open"
    assert refreshed_issue.version == initial_version

    # Verify no history record was written
    history_count = db_session.query(IssueStatusHistory).filter_by(issue_id=issue.id).count()
    assert history_count == 0
