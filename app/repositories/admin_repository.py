from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_model import AdminUser
from app.repositories.base_repository import BaseRepository


class AdminUserRepository(BaseRepository[AdminUser]):
    """Data access for admin portal accounts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AdminUser)

    async def get_admin_by_username(self, username: str) -> AdminUser | None:
        """Fetch one admin account by unique username."""
        stmt = select(AdminUser).where(AdminUser.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_admin_by_id(self, admin_id: int) -> AdminUser | None:
        """Fetch one admin account by primary key."""
        return await self.get_by_id(admin_id)
