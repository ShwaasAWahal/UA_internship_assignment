from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Issue, IssueStatusHistory, User
from app.schemas import IssueCreate, IssueStatusUpdate, IssueUpdate
from app.workflow import validate_status_transition


class ConcurrencyConflictError(Exception):
    """Raised when an update fails due to a version mismatch."""
    pass


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Retrieve user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def list_demo_users(db: Session) -> list[User]:
    """Retrieve all seeded demo users ordered by ID."""
    return db.query(User).order_by(User.id).all()


def create_issue(db: Session, owner_id: str, data: IssueCreate) -> Issue:
    """Create a new accessibility issue owned by the given user."""
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
    """Retrieve an issue strictly scoped to the owner ID.

    Returns None if the issue does not exist or belongs to another user,
    preventing IDOR and resource enumeration.
    """
    return (
        db.query(Issue)
        .filter(Issue.id == issue_id, Issue.owner_id == owner_id)
        .first()
    )


def list_issues_by_owner(
    db: Session,
    owner_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> list[Issue]:
    """List issues owned by a user with optional status and severity filtering."""
    query = db.query(Issue).filter(Issue.owner_id == owner_id)
    if status:
        query = query.filter(Issue.status == status)
    if severity:
        query = query.filter(Issue.severity == severity)
    return query.order_by(Issue.created_at.desc(), Issue.id.desc()).all()


def update_issue_details(
    db: Session,
    issue: Issue,
    data: IssueUpdate,
) -> Issue:
    """Update issue details using optimistic locking against the version number."""
    if issue.version != data.version:
        raise ConcurrencyConflictError(
            f"Conflict: Issue version {data.version} does not match current database version {issue.version}. Please refresh."
        )

    if data.title is not None:
        issue.title = data.title
    if data.description is not None:
        issue.description = data.description
    if data.page_url is not None:
        issue.page_url = data.page_url
    if data.wcag_criterion is not None:
        issue.wcag_criterion = data.wcag_criterion
    if data.severity is not None:
        issue.severity = data.severity.value

    issue.version += 1
    issue.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(issue)
    return issue


def transition_issue_status(
    db: Session,
    issue: Issue,
    actor_id: str,
    data: IssueStatusUpdate,
) -> tuple[Issue, IssueStatusHistory]:
    """Transition an issue's status, validate against the workflow, check version, and record history."""
    if issue.version != data.version:
        raise ConcurrencyConflictError(
            f"Conflict: Issue version {data.version} does not match current database version {issue.version}. Please refresh."
        )

    target_status = data.status.value
    validate_status_transition(issue.status, target_status)

    from_status = issue.status
    now_utc = datetime.now(timezone.utc)

    issue.status = target_status
    issue.version += 1
    issue.updated_at = now_utc

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
    db.refresh(history_entry)
    return issue, history_entry
