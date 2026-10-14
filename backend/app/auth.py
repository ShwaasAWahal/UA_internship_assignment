from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.seed import ALLOWED_DEMO_USER_IDS, DEFAULT_DEMO_USER_ID


def get_current_user(
    x_demo_user_id: Optional[str] = Header(None, alias="X-Demo-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the active demo user from the request header.

    Local Demo Authentication Mechanism:
    -----------------------------------
    This application simulates user sessions locally using the `X-Demo-User-Id` HTTP header.
    Only strictly pre-seeded demo user IDs are permitted (`demo-user-alice`, `demo-user-bob`).
    Any attempt to supply an arbitrary user ID or impersonate an unseeded entity is rejected
    with 401 Unauthorized. If no header is sent, it safely defaults to `demo-user-alice`.

    Note: This is strictly for local demonstration purposes and is NOT production authentication.
    """
    user_id = x_demo_user_id.strip() if x_demo_user_id else DEFAULT_DEMO_USER_ID

    if user_id not in ALLOWED_DEMO_USER_IDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED_DEMO_IDENTITY",
                "message": (
                    f"Invalid demo identity: '{x_demo_user_id}'. Only configured demo users "
                    f"({', '.join(sorted(ALLOWED_DEMO_USER_IDS))}) can be selected."
                ),
            },
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "DEMO_USER_NOT_INITIALIZED",
                "message": f"Demo user '{user_id}' was not found in the database. Ensure database is seeded.",
            },
        )

    return user
