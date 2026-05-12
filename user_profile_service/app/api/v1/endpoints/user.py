from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.auth import get_db, get_current_user
from app.services import user_service
from app.schemas.common import APIResponse
from app.schemas.user import UserResponse

router = APIRouter()

@router.get("/me", response_model=APIResponse[UserResponse])
def get_me(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    user = user_service.get_user(db, user_id)
    return APIResponse[UserResponse](
        success=True,
        message="User profile retrieved successfully",
        data=UserResponse.model_validate(user),
    )


@router.patch("/me", response_model=APIResponse[UserResponse])
def update_me(payload: dict, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    user = user_service.update_user(db, user_id, payload)
    return APIResponse[UserResponse](
        success=True,
        message="User profile updated successfully",
        data=UserResponse.model_validate(user),
    )
