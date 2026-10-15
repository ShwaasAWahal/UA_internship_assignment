from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import update
from sqlalchemy.orm import Session, joinedload

from app.models import Issue, IssueStatusHistory, User
from app.schemas import IssueCreate, IssueStatusUpdate, IssueUpdate
from app.workflow import InvalidStatusTransitionError, validate_status_transition


class ConcurrencyConflictError(Exception):
    """Raised when an update fails due to an optimistic concurrency version mismatch."""

    def __init__(self, message: str = "Conflict: The issue was modified by another operation. Please refresh."):
        self.message = message
        super().__init__(self.message)


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Retrieve user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def list_demo_users(db: Session) -> list[User]:
    """Retrieve all seeded demo users ordered by ID."""
    return db.query(User).order_by(User.id).all()


def create_issue(db: Session, owner_id: str, data: IssueCreate) -> Issue:
    """Create a new accessibility issue owned strictly by the authenticated demo user."""
    issue = Issue(
        owner_id=owner_id,
        title=data.title,
        description=data.description,
        page_url=data.page_url,
        wcag_criterion=data.wcag_criterion,
        severity=data.severity.value,
        status="Open",
        version=1,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def get_issue_by_id_and_owner(db: Session, issue_id: int, owner_id: str) -> Optional[Issue]:
    """Retrieve an issue strictly scoped to the owner ID, including its full status audit history.

    Returns None if the issue does not exist or belongs to another user,
    preventing IDOR and resource enumeration.
    """
    return (
        db.query(Issue)
        .options(joinedload(Issue.status_history))
        .filter(Issue.id == issue_id, Issue.owner_id == owner_id)
        .first()
    )


def list_issues_by_owner(
    db: Session,
    owner_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Issue], int]:
    """List issues owned by a user with optional status and severity filtering,

    deterministic sorting (created_at DESC, id DESC), and bounded pagination.
    Returns (items, total_count).
    """
    query = db.query(Issue).filter(Issue.owner_id == owner_id)
    if status:
        query = query.filter(Issue.status == status)
    if severity:
        query = query.filter(Issue.severity == severity)

    total = query.count()
    items = (
        query.order_by(Issue.created_at.desc(), Issue.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def update_issue_details(
    db: Session,
    issue_id: int,
    owner_id: str,
    data: IssueUpdate,
) -> Optional[Issue]:
    """Update permitted issue details using optimistic locking against the version number.

    Returns:
    - None if the issue does not exist or is not owned by the caller (maps to 404).
    - Raises ConcurrencyConflictError if version does not match current state (maps to 409).
    - Updated Issue on successful commit.
    """
    # Verify issue exists within authorized scope
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.owner_id == owner_id).first()
    if not issue:
        return None

    # Version check
    if issue.version != data.version:
        raise ConcurrencyConflictError(
            f"Conflict: Issue version {data.version} does not match current database version {issue.version}. Please refresh."
        )

    now_utc = datetime.now(timezone.utc)
    update_values: dict[str, Any] = {
        "version": Issue.version + 1,
        "updated_at": now_utc,
    }
    if data.title is not None:
        update_values["title"] = data.title
    if data.description is not None:
        update_values["description"] = data.description
    if data.page_url is not None:
        update_values["page_url"] = data.page_url
    if data.wcag_criterion is not None:
        update_values["wcag_criterion"] = data.wcag_criterion
    if data.severity is not None:
        update_values["severity"] = data.severity.value

    # Atomic DB-level conditional update
    stmt = (
        update(Issue)
        .where(
            Issue.id == issue_id,
            Issue.owner_id == owner_id,
            Issue.version == data.version,
        )
        .values(**update_values)
    )
    result = db.execute(stmt)
    if result.rowcount == 0:
        db.rollback()
        raise ConcurrencyConflictError(
            "Conflict: Issue was modified concurrently by another update. Please refresh."
        )

    db.commit()
    db.refresh(issue)
    return issue


def transition_issue_status(
    db: Session,
    issue_id: int,
    owner_id: str,
    actor_id: str,
    data: IssueStatusUpdate,
) -> Optional[Issue]:
    """Transition an issue's status with workflow validation and optimistic concurrency.

    Both the issue status update and the status history entry are committed in a single transaction.
    Returns None if the issue does not exist or is not owned by the caller (maps to 404).
    """
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.owner_id == owner_id).first()
    if not issue:
        return None

    # Version check
    if issue.version != data.version:
        raise ConcurrencyConflictError(
            f"Conflict: Issue version {data.version} does not match current database version {issue.version}. Please refresh."
        )

    target_status = data.status.value
    # Workflow validation will raise InvalidStatusTransitionError if invalid or no-op
    validate_status_transition(issue.status, target_status)

    from_status = issue.status
    now_utc = datetime.now(timezone.utc)

    # Atomic conditional update at database level
    stmt = (
        update(Issue)
        .where(
            Issue.id == issue_id,
            Issue.owner_id == owner_id,
            Issue.version == data.version,
        )
        .values(
            status=target_status,
            version=Issue.version + 1,
            updated_at=now_utc,
        )
    )
    result = db.execute(stmt)
    if result.rowcount == 0:
        db.rollback()
        raise ConcurrencyConflictError(
            "Conflict: Issue was modified concurrently by another update. Please refresh."
        )

    # Append audit history row in same transaction
    history_entry = IssueStatusHistory(
        issue_id=issue.id,
        actor_id=actor_id,
        previous_status=from_status,
        new_status=target_status,
        changed_at=now_utc,
        comment=data.comment,
    )
    db.add(history_entry)

    db.commit()
    db.refresh(issue)
    return issue
