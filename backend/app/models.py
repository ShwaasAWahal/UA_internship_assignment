from datetime import datetime, timezone
import enum
from typing import Any
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import relationship, synonym

from app.database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime type that guarantees timezone-aware UTC datetimes across SQLite and PostgreSQL."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class SeverityEnum(str, enum.Enum):
    MINOR = "Minor"
    MODERATE = "Moderate"
    SERIOUS = "Serious"
    CRITICAL = "Critical"


class StatusEnum(str, enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class User(Base):
    """User entity representing audit team members."""

    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="auditor")
    team_id = Column(String(64), nullable=True)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)

    # Relationships
    issues = relationship(
        "Issue",
        back_populates="owner",
        foreign_keys="Issue.owner_id",
        cascade="all, delete-orphan",
    )
    status_history_entries = relationship(
        "IssueStatusHistory",
        back_populates="actor",
        foreign_keys="IssueStatusHistory.actor_id",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} name={self.display_name!r}>"


class Issue(Base):
    """Accessibility issue reported on an audited web page."""

    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(64), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    page_url = Column(String(2048), nullable=False)
    wcag_criterion = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=StatusEnum.OPEN.value)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)
    updated_at = Column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Alias reporter_id to owner_id for compatibility with ARCHITECTURE.md specification
    reporter_id = synonym("owner_id")

    # Relationships
    owner = relationship(
        "User",
        back_populates="issues",
        foreign_keys=[owner_id],
    )
    status_history = relationship(
        "IssueStatusHistory",
        back_populates="issue",
        foreign_keys="IssueStatusHistory.issue_id",
        cascade="all, delete-orphan",
        order_by="desc(IssueStatusHistory.changed_at)",
    )

    __table_args__ = (
        Index("ix_issues_owner_created", "owner_id", "created_at"),
        Index("ix_issues_status_created", "status", "created_at"),
        Index("ix_issues_severity", "severity"),
        Index("ix_issues_owner_status_created", "owner_id", "status", "created_at"),
        Index("ix_issues_owner_severity_created", "owner_id", "severity", "created_at"),
        CheckConstraint(
            "severity IN ('Minor', 'Moderate', 'Serious', 'Critical')",
            name="ck_issues_severity",
        ),
        CheckConstraint(
            "status IN ('Open', 'In Progress', 'Resolved')",
            name="ck_issues_status",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_issues_version",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_issues_title_not_blank",
        ),
    )

    def __repr__(self) -> str:
        return f"<Issue id={self.id} title={self.title!r} status={self.status!r} owner={self.owner_id!r}>"


class IssueStatusHistory(Base):
    """Persistent audit log of issue status transitions."""

    __tablename__ = "issue_status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(64), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    previous_status = Column(String(20), nullable=False)
    new_status = Column(String(20), nullable=False)
    changed_at = Column(UTCDateTime, nullable=False, default=utc_now, index=True)
    comment = Column(Text, nullable=True)

    # Relationships
    issue = relationship(
        "Issue",
        back_populates="status_history",
        foreign_keys=[issue_id],
    )
    actor = relationship(
        "User",
        back_populates="status_history_entries",
        foreign_keys=[actor_id],
    )

    __table_args__ = (
        Index("ix_history_issue_changed_at", "issue_id", "changed_at"),
        CheckConstraint(
            "previous_status IN ('Open', 'In Progress', 'Resolved')",
            name="ck_history_previous_status",
        ),
        CheckConstraint(
            "new_status IN ('Open', 'In Progress', 'Resolved')",
            name="ck_history_new_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<IssueStatusHistory id={self.id} issue_id={self.issue_id} {self.previous_status}->{self.new_status}>"
