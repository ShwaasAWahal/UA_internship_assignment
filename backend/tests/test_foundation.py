from datetime import timezone
import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import crud
from app.database import Base
from app.models import Issue, IssueStatusHistory, SeverityEnum, StatusEnum, User
from app.schemas import IssueCreate
from app.seed import DEMO_USERS, init_db_and_seed


def test_demo_users_seeded(db_session):
    """Verify that exactly two predictable demo users exist in the database."""
    users = db_session.query(User).all()
    user_ids = {u.id for u in users}
    assert len(users) == 2
    assert "demo-user-alice" in user_ids
    assert "demo-user-bob" in user_ids

    alice = db_session.query(User).filter_by(id="demo-user-alice").first()
    assert alice.email == "alice@unifiedaccessibility.demo"
    assert "Alice" in alice.display_name

    bob = db_session.query(User).filter_by(id="demo-user-bob").first()
    assert bob.email == "bob@unifiedaccessibility.demo"
    assert "Bob" in bob.display_name


def test_model_persistence_and_relationships(db_session):
    """Verify that Issue and IssueStatusHistory models persist with UTC timestamps and relationships."""
    alice = db_session.query(User).filter_by(id="demo-user-alice").first()
    assert alice is not None

    # Create issue via CRUD service
    issue_data = IssueCreate(
        title="Images missing alternative text",
        description="Navigation logo and hero banner do not include alt attributes.",
        page_url="https://example.com/home",
        wcag_criterion="1.1.1 Non-text Content",
        severity=SeverityEnum.CRITICAL,
    )
    issue = crud.create_issue(db_session, owner_id=alice.id, data=issue_data)

    assert issue.id is not None
    assert issue.owner_id == "demo-user-alice"
    assert issue.reporter_id == "demo-user-alice"  # synonym compatibility
    assert issue.status == "Open"
    assert issue.version == 1
    assert issue.created_at is not None
    # Ensure timezone-aware UTC
    assert issue.created_at.tzinfo is not None or issue.created_at.utcoffset() is not None
    assert issue.updated_at is not None

    # Create status history record
    history = IssueStatusHistory(
        issue_id=issue.id,
        actor_id=alice.id,
        previous_status=StatusEnum.OPEN.value,
        new_status=StatusEnum.IN_PROGRESS.value,
        comment="Started audit verification.",
    )
    db_session.add(history)
    db_session.commit()

    # Query back and check relationships
    reloaded_issue = db_session.query(Issue).filter_by(id=issue.id).first()
    assert len(reloaded_issue.status_history) == 1
    assert reloaded_issue.status_history[0].new_status == "In Progress"
    assert reloaded_issue.status_history[0].actor.id == "demo-user-alice"
    assert reloaded_issue.owner.email == "alice@unifiedaccessibility.demo"


def test_foreign_key_enforcement(db_session):
    """Verify that foreign key constraints are enforced (e.g., non-existent owner)."""
    invalid_issue = Issue(
        owner_id="non-existent-user-id",
        title="Invalid Issue",
        page_url="https://example.com",
        severity="Minor",
        status="Open",
        version=1,
    )
    db_session.add(invalid_issue)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_demo_user_impersonation_prevention(client):
    """Verify that arbitrary user impersonation is denied and only whitelisted demo users can be selected."""
    # Alice selection
    res_alice = client.get("/api/me", headers={"X-Demo-User-Id": "demo-user-alice"})
    assert res_alice.status_code == 200
    assert res_alice.json()["id"] == "demo-user-alice"

    # Bob selection
    res_bob = client.get("/api/me", headers={"X-Demo-User-Id": "demo-user-bob"})
    assert res_bob.status_code == 200
    assert res_bob.json()["id"] == "demo-user-bob"

    # Default fallback when no header is supplied
    res_default = client.get("/api/me")
    assert res_default.status_code == 200
    assert res_default.json()["id"] == "demo-user-alice"

    # Impersonation attempt with an arbitrary / unseeded user ID must fail with 401
    res_attacker = client.get("/api/me", headers={"X-Demo-User-Id": "arbitrary-attacker-id"})
    assert res_attacker.status_code == 401
    body = res_attacker.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED_DEMO_IDENTITY"


def test_health_endpoints(client):
    """Verify health check returns valid JSON status and timestamp."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "timestamp" in data


def test_demo_users_list_endpoint(client):
    """Verify that UI switcher can retrieve available demo users."""
    response = client.get("/api/users/demo")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2
    ids = {u["id"] for u in users}
    assert ids == {"demo-user-alice", "demo-user-bob"}


def test_sqlite_persistence_between_restarts():
    """Verify that SQLite database data persists across connection restarts."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=engine)

        # First run: initialize and write data
        Base.metadata.create_all(bind=engine)
        session1 = Session()
        init_db_and_seed(session1)

        issue_data = IssueCreate(
            title="Persistent test issue",
            page_url="https://example.com/test",
            severity=SeverityEnum.SERIOUS,
        )
        crud.create_issue(session1, owner_id="demo-user-alice", data=issue_data)
        session1.close()
        engine.dispose()

        # Simulate restart: new engine and session connecting to same SQLite file
        new_engine = create_engine(db_url, connect_args={"check_same_thread": False})
        NewSession = sessionmaker(bind=new_engine)
        session2 = NewSession()

        # Idempotent re-initialization on startup should not drop data
        init_db_and_seed(session2)

        persisted_issue = session2.query(Issue).filter_by(title="Persistent test issue").first()
        assert persisted_issue is not None
        assert persisted_issue.owner_id == "demo-user-alice"
        assert persisted_issue.severity == "Serious"

        # Demo users still intact
        user_count = session2.query(User).count()
        assert user_count == 2

        session2.close()
        new_engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
