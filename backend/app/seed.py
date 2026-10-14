import logging
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import User

logger = logging.getLogger(__name__)

# Exactly two predictable demo users required by the assignment specification
DEMO_USERS: dict[str, dict[str, str]] = {
    "demo-user-alice": {
        "id": "demo-user-alice",
        "email": "alice@unifiedaccessibility.demo",
        "display_name": "Alice Chen (Lead Auditor)",
        "role": "lead_auditor",
        "team_id": "team-accessibility-core",
    },
    "demo-user-bob": {
        "id": "demo-user-bob",
        "email": "bob@unifiedaccessibility.demo",
        "display_name": "Bob Martinez (Auditor)",
        "role": "auditor",
        "team_id": "team-accessibility-core",
    },
}

ALLOWED_DEMO_USER_IDS: set[str] = set(DEMO_USERS.keys())
DEFAULT_DEMO_USER_ID: str = "demo-user-alice"


def init_db_and_seed(db: Session) -> None:
    """Initialize database tables and seed predictable demo accounts without wiping existing data.

    This function is idempotent. It ensures that schema tables are created if missing,
    and inserts demo user records if they do not already exist. It does NOT delete
    or overwrite existing issues, history, or user data.
    """
    # Create tables if not present
    Base.metadata.create_all(bind=engine)

    # Seed demo users if missing
    for user_id, user_data in DEMO_USERS.items():
        existing_user = db.query(User).filter(User.id == user_id).first()
        if not existing_user:
            user = User(
                id=user_data["id"],
                email=user_data["email"],
                display_name=user_data["display_name"],
                role=user_data["role"],
                team_id=user_data["team_id"],
            )
            db.add(user)
            logger.info("Seeded demo user: %s (%s)", user.id, user.email)

    db.commit()
