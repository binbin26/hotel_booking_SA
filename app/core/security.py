from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.schemas.admin_schema import AdminTokenPayload
from app.schemas.auth_schema import TokenPayload, UserRole

settings = get_settings()


def create_access_token(
    subject: int,
    role: UserRole,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for the given user."""
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(subject),
        "role": role.value,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> TokenPayload:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return TokenPayload.model_validate(payload)
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the given plain-text password."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when the plain password matches the stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_admin_access_token(
    admin_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT for an authenticated admin portal session."""
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(admin_id),
        "token_type": "admin",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_admin_token(token: str) -> AdminTokenPayload:
    """Decode and validate an admin portal JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return AdminTokenPayload.model_validate(payload)
    except JWTError as exc:
        raise ValueError("Invalid or expired admin token") from exc
