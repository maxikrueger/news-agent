"""Security utilities: JWT, password hashing, authentication"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer for JWT
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token"""
    to_encode: dict[str, Any] = {"sub": str(user_id)}

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> int | None:
    """Verify a JWT token and return user_id"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None


async def get_current_user(request: Request, credentials=Depends(security)) -> int:
    """Get current authenticated user from JWT token (header or httpOnly cookie)"""
    token = None

    # Try Bearer token in Authorization header first
    if credentials is not None:
        token = credentials.credentials
    # Fall back to httpOnly cookie
    elif request is not None:
        token = request.cookies.get("auth_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


def generate_verification_token(user_id: int) -> str:
    """Generate a verification token for email verification"""
    to_encode: dict[str, Any] = {"sub": str(user_id), "type": "email_verification"}
    expire = datetime.now(UTC) + timedelta(hours=24)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_verification_token(token: str) -> int | None:
    """Verify an email verification token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "email_verification":
            return None

        return int(user_id)
    except JWTError:
        return None


def generate_password_reset_token(user_id: int) -> str:
    """Generate a password reset token"""
    to_encode: dict[str, Any] = {"sub": str(user_id), "type": "password_reset"}
    expire = datetime.now(UTC) + timedelta(hours=1)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password_reset_token(token: str) -> int | None:
    """Verify a password reset token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "password_reset":
            return None

        return int(user_id)
    except JWTError:
        return None
