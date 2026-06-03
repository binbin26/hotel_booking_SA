from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings
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
