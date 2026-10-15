from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import SeverityEnum, StatusEnum, User
from app.schemas import (
    IssueCreate,
    IssueResponse,
    IssueStatusUpdate,
    IssueUpdate,
    PaginatedIssuesResponse,
)
from app.workflow import InvalidStatusTransitionError

router = APIRouter(prefix="/api/issues", tags=["Issues"])


@router.get("", response_model=PaginatedIssuesResponse)
def list_issues(
    status: Optional[StatusEnum] = Query(None, description="Filter by status"),
    severity: Optional[SeverityEnum] = Query(None, description="Filter by severity"),
    limit: int = Query(20, ge=1, le=100, description="Bounded page size (1-100)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedIssuesResponse:
    """List issues scoped strictly to the authenticated user with status/severity filters and bounded pagination."""
    status_filter = status.value if status else None
    severity_filter = severity.value if severity else None

    items, total = crud.list_issues_by_owner(
        db=db,
        owner_id=current_user.id,
        status=status_filter,
        severity=severity_filter,
        limit=limit,
        offset=offset,
    )

    return PaginatedIssuesResponse(
        items=[IssueResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_issue(
    data: IssueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """Create a new accessibility issue owned by the current demo user."""
    issue = crud.create_issue(
        db=db,
        owner_id=current_user.id,
        data=data,
    )
    return IssueResponse.model_validate(issue)


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """Retrieve an issue and its complete status change history.

    Returns 404 if the issue does not exist or is not owned by the caller,
    preventing IDOR and resource disclosure.
    """
    issue = crud.get_issue_by_id_and_owner(
        db=db,
        issue_id=issue_id,
        owner_id=current_user.id,
    )
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ISSUE_NOT_FOUND",
                "message": f"Issue #{issue_id} not found.",
            },
        )
    return IssueResponse.model_validate(issue)


@router.patch("/{issue_id}", response_model=IssueResponse)
def update_issue(
    issue_id: int,
    data: IssueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """Edit permitted issue fields using optimistic concurrency control.

    Returns 404 if unauthorized/nonexistent, or 409 on version conflict.
    """
    try:
        issue = crud.update_issue_details(
            db=db,
            issue_id=issue_id,
            owner_id=current_user.id,
            data=data,
        )
    except crud.ConcurrencyConflictError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONCURRENCY_CONFLICT",
                "message": err.message,
            },
        )

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ISSUE_NOT_FOUND",
                "message": f"Issue #{issue_id} not found.",
            },
        )

    return IssueResponse.model_validate(issue)


@router.patch("/{issue_id}/status", response_model=IssueResponse)
def update_issue_status(
    issue_id: int,
    data: IssueStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """Transition issue status, append history record, and verify optimistic concurrency version.

    Rejects invalid transitions and concurrent stale requests with HTTP 409 Conflict.
    """
    try:
        issue = crud.transition_issue_status(
            db=db,
            issue_id=issue_id,
            owner_id=current_user.id,
            actor_id=current_user.id,
            data=data,
        )
    except InvalidStatusTransitionError as err:
        fields = (
            {"status": "Choose an allowed next status."}
            if err.target_status == "In Progress"
            else {"status": err.message}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATUS_TRANSITION",
                "message": err.message,
                "fields": fields,
            },
        )
    except crud.ConcurrencyConflictError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONCURRENCY_CONFLICT",
                "message": err.message,
            },
        )

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ISSUE_NOT_FOUND",
                "message": f"Issue #{issue_id} not found.",
            },
        )

    return IssueResponse.model_validate(issue)
