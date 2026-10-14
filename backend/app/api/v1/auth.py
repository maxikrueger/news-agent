"""Authentication endpoints"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
)
from app.db.database import get_db
from app.schemas.user import (
    ChangePasswordRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user"""
    user = AuthService.register(db, user_create)
    token = create_access_token(user_id=user.id)

    is_prod = settings.is_production
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return TokenResponse(access_token=token, token_type="bearer", user_id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(user_login: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login user"""
    user, token = AuthService.login(db, user_login)

    is_prod = settings.is_production
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return TokenResponse(access_token=token, token_type="bearer", user_id=user.id, email=user.email)


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with token"""
    user = AuthService.verify_email(db, request.token)
    return UserResponse.model_validate(user)


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info"""
    user = AuthService.get_user(db, user_id)
    return UserResponse.model_validate(user)


@router.post("/password-reset/request")
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset"""
    # In production, would send email here
    # For MVP, just return success
    result = AuthService.request_password_reset(db, request.email)
    return result


@router.post("/password-reset/confirm", response_model=UserResponse)
async def confirm_password_reset(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password with token"""
    user = AuthService.reset_password(db, request.token, request.new_password)
    return UserResponse.model_validate(user)


@router.post("/password-change", response_model=UserResponse)
async def change_password(
    request: ChangePasswordRequest, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    user = AuthService.change_password(db, user_id, request.old_password, request.new_password)
    return UserResponse.model_validate(user)
