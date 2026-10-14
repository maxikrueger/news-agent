"""Authentication service with business logic"""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
    verify_verification_token,
)
from app.db.models import User
from app.schemas.user import UserCreate, UserLogin


class AuthService:
    @staticmethod
    def register(db: Session, user_create: UserCreate) -> User:
        """Register a new user"""
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_create.email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        # Create new user
        user = User(email=user_create.email, password_hash=hash_password(user_create.password))

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User registration failed"
            ) from None

    @staticmethod
    def login(db: Session, user_login: UserLogin) -> tuple[User, str]:
        """Authenticate user and return user + token"""
        user = db.query(User).filter(User.email == user_login.email).first()

        if not user or not verify_password(user_login.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        token = create_access_token(user_id=user.id)
        return user, token

    @staticmethod
    def verify_email(db: Session, token: str) -> User:
        """Verify email using token"""
        user_id = verify_verification_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.email_verified = True
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def request_password_reset(db: Session, email: str) -> dict:
        """Request password reset (returns success regardless of email existence for security)"""
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Return success for security reasons (don't reveal if email exists)
            return {"message": "If the email exists, a reset link has been sent"}

        # In real app, would send email here with reset token
        # For now, just return success
        return {"message": "If the email exists, a reset link has been sent"}

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> User:
        """Reset password using token"""
        user_id = verify_password_reset_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.password_hash = hash_password(new_password)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        """Get user by ID"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> User:
        """Change password for authenticated user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Verify old password
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
            )

        # Set new password
        user.password_hash = hash_password(new_password)
        db.commit()
        db.refresh(user)
        return user
