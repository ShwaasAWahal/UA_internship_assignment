from app.models import StatusEnum


class InvalidStatusTransitionError(Exception):
    """Raised when an issue status transition violates the workflow state machine."""

    def __init__(self, current_status: str, target_status: str, message: str | None = None):
        self.current_status = current_status
        self.target_status = target_status
        self.message = message or (
            f"An issue cannot transition directly from '{current_status}' to '{target_status}'. "
            f"Allowed next statuses from '{current_status}' are: {', '.join(sorted(ALLOWED_TRANSITIONS.get(current_status, set())))}."
        )
        super().__init__(self.message)


# Allowed transitions specified in ARCHITECTURE.md Section 5
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    StatusEnum.OPEN.value: {StatusEnum.IN_PROGRESS.value, StatusEnum.RESOLVED.value},
    StatusEnum.IN_PROGRESS.value: {StatusEnum.RESOLVED.value, StatusEnum.OPEN.value},
    StatusEnum.RESOLVED.value: {StatusEnum.OPEN.value},
}


def validate_status_transition(current_status: str, target_status: str) -> None:
    """Validate whether transitioning from current_status to target_status is permitted.

    Rules:
    - Same status is rejected (no-op).
    - Resolved -> In Progress is explicitly disallowed (must reopen to Open first).
    - Throws InvalidStatusTransitionError on violation.
    """
    if current_status == target_status:
        raise InvalidStatusTransitionError(
            current_status,
            target_status,
            f"Issue is already in status '{current_status}'.",
        )

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            current_status,
            target_status,
            f"An issue cannot move from '{current_status}' directly to '{target_status}'. "
            f"Allowed transitions from '{current_status}': {', '.join(sorted(allowed)) or 'None'}.",
        )
