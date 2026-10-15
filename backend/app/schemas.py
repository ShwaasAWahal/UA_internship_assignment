from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import SeverityEnum, StatusEnum


class ErrorDetail(BaseModel):
    """Structured error object adhering to ARCHITECTURE.md specifications."""

    code: str
    message: str
    fields: Optional[dict[str, str]] = None


class ErrorEnvelope(BaseModel):
    """Standardized API error response wrapper."""

    error: ErrorDetail


class UserResponse(BaseModel):
    """Public user identity information."""

    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueStatusHistoryResponse(BaseModel):
    """Status history audit trail entry."""

    id: int
    issue_id: int
    actor_id: str
    previous_status: str
    new_status: str
    changed_at: datetime
    comment: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def validate_http_url(url: str) -> str:
    """Validate that a URL string is a well-formed HTTP or HTTPS URL."""
    if not url or not isinstance(url, str):
        raise ValueError("Page URL is required.")
    stripped = url.strip()
    parsed = urlparse(stripped)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Page URL must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("Page URL must contain a valid domain or host.")
    return stripped


class IssueBase(BaseModel):
    """Shared issue fields."""

    title: str = Field(..., min_length=1, max_length=255, description="Issue title")
    description: Optional[str] = Field(None, description="Detailed description of the issue")
    page_url: str = Field(..., max_length=2048, description="Web page URL where issue was found")
    wcag_criterion: Optional[str] = Field(None, max_length=100, description="WCAG Success Criterion")
    severity: SeverityEnum = Field(..., description="Severity level")

    @field_validator("title")
    @classmethod
    def title_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title cannot be empty or only whitespace.")
        return stripped

    @field_validator("page_url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        return validate_http_url(v)


class IssueCreate(IssueBase):
    """Payload to create a new accessibility issue."""

    model_config = ConfigDict(extra="forbid")


class IssueUpdate(BaseModel):
    """Payload to edit issue details with optimistic concurrency version."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    page_url: Optional[str] = Field(None, max_length=2048)
    wcag_criterion: Optional[str] = Field(None, max_length=100)
    severity: Optional[SeverityEnum] = None
    version: int = Field(..., description="Expected issue version for concurrency control")

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def title_not_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Title cannot be empty or only whitespace.")
            return stripped
        return v

    @field_validator("page_url")
    @classmethod
    def url_must_be_http(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_http_url(v)
        return v


class IssueStatusUpdate(BaseModel):
    """Payload to transition issue status with optimistic concurrency control."""

    status: StatusEnum = Field(..., description="Target status")
    version: int = Field(..., description="Current version of the issue")
    comment: Optional[str] = Field(None, description="Optional transition comment")

    model_config = ConfigDict(extra="forbid")


class IssueResponse(BaseModel):
    """Representation of an issue returned to the client."""

    id: int
    owner_id: str
    title: str
    description: Optional[str] = None
    page_url: str
    wcag_criterion: Optional[str] = None
    severity: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    status_history: Optional[list[IssueStatusHistoryResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedIssuesResponse(BaseModel):
    """Paginated collection of issues for the current authorized scope."""

    items: list[IssueResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Health check endpoint response."""

    status: str
    database: str
    version: str
    timestamp: datetime
