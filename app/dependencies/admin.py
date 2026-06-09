from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions.auth_exceptions import (
    AdminNotAuthenticatedException,
    AdminNotFoundException,
    InvalidCredentialsException,
)
from app.models.admin_model import AdminUser
from app.repositories.admin_repository import AdminUserRepository
from app.services.admin_auth_service import AdminAuthService


def get_admin_repository(
    db: AsyncSession = Depends(get_db),
) -> AdminUserRepository:
    """Provide AdminUserRepository bound to the request session."""
    return AdminUserRepository(db)


def get_admin_auth_service(
    admin_repo: AdminUserRepository = Depends(get_admin_repository),
) -> AdminAuthService:
    """Provide AdminAuthService with its repository dependency."""
    return AdminAuthService(admin_repo)


def _read_admin_session_token(request: Request) -> str | None:
    from app.core.config import get_settings

    settings = get_settings()
    return request.cookies.get(settings.ADMIN_TOKEN_COOKIE_NAME)


async def get_current_admin(
    request: Request,
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminUser:
    """Authenticate the caller from the HttpOnly admin session cookie."""
    try:
        return await admin_auth_service.resolve_admin_from_token(
            _read_admin_session_token(request),
        )
    except AdminNotAuthenticatedException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        ) from exc
    except (AdminNotFoundException, InvalidCredentialsException) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session",
        ) from exc


async def get_current_admin_or_none(
    request: Request,
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminUser | None:
    """Return the active admin session or None when the cookie is missing/invalid."""
    try:
        return await admin_auth_service.resolve_admin_from_token(
            _read_admin_session_token(request),
        )
    except (AdminNotAuthenticatedException, AdminNotFoundException, InvalidCredentialsException):
        return None
