import logging

from app.core.security import (
    create_admin_access_token,
    verify_admin_token,
    verify_password,
)
from app.exceptions.auth_exceptions import (
    AdminNotAuthenticatedException,
    AdminNotFoundException,
    InvalidCredentialsException,
)
from app.models.admin_model import AdminUser
from app.repositories.admin_repository import AdminUserRepository
from app.schemas.admin_schema import AdminLoginResponse, AdminUserResponse

logger = logging.getLogger(__name__)


class AdminAuthService:
    """Business logic for admin portal authentication."""

    def __init__(self, admin_repo: AdminUserRepository) -> None:
        self._admin_repo = admin_repo

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> AdminLoginResponse:
        """
        Verify admin credentials and issue a JWT access token.

        Raises:
            InvalidCredentialsException: When username/password is wrong or inactive.
        """
        admin = await self._admin_repo.get_admin_by_username(username)
        if admin is None or not admin.is_active:
            logger.warning("Failed admin login for username=%s", username)
            raise InvalidCredentialsException()

        if not verify_password(password, admin.hashed_password):
            logger.warning("Invalid password for admin username=%s", username)
            raise InvalidCredentialsException()

        token = create_admin_access_token(admin.id)
        logger.info("Admin authenticated successfully username=%s", username)
        return AdminLoginResponse(
            access_token=token,
            admin=AdminUserResponse.model_validate(admin),
        )

    async def get_active_admin(self, admin_id: int) -> AdminUser:
        """
        Load an active admin account by id.

        Raises:
            AdminNotFoundException: When the admin row does not exist.
            InvalidCredentialsException: When the admin account is inactive.
        """
        admin = await self._admin_repo.get_admin_by_id(admin_id)
        if admin is None:
            raise AdminNotFoundException(admin_id)
        if not admin.is_active:
            raise InvalidCredentialsException()
        return admin

    async def resolve_admin_from_token(self, token: str | None) -> AdminUser:
        """
        Validate a session token and return the matching active admin.

        Raises:
            AdminNotAuthenticatedException: When the token is missing or invalid.
            AdminNotFoundException: When the token subject is not found.
            InvalidCredentialsException: When the admin account is inactive.
        """
        if not token:
            raise AdminNotAuthenticatedException()

        try:
            payload = verify_admin_token(token)
        except ValueError as exc:
            logger.warning("Invalid admin session token: %s", exc)
            raise AdminNotAuthenticatedException() from exc

        return await self.get_active_admin(payload.sub)
