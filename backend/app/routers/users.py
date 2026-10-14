from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/api", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the current active demo user."""
    return UserResponse.model_validate(current_user)


@router.get("/users/demo", response_model=list[UserResponse])
def get_demo_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    """Return the list of predictable demo users available for local selection."""
    users = crud.list_demo_users(db)
    return [UserResponse.model_validate(u) for u in users]
