"""Repository for notification logs."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_log import NotificationLog, InteractionType


class NotificationLogRepository:
    """Repository for handling notification log operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(
        self,
        booking_id: int,
        interaction_type: InteractionType,
        guest_name: str,
        message: str,
        action: Optional[str] = None,
    ) -> NotificationLog:
        """Create and save a new notification log."""
        log = NotificationLog(
            booking_id=booking_id,
            interaction_type=interaction_type,
            guest_name=guest_name,
            message=message,
            action=action,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_logs_by_booking_id(
        self,
        booking_id: int,
        limit: int = 50,
    ) -> list[NotificationLog]:
        """Get all notification logs for a booking."""
        stmt = (
            select(NotificationLog)
            .where(NotificationLog.booking_id == booking_id)
            .order_by(desc(NotificationLog.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent_logs(
        self,
        limit: int = 100,
    ) -> list[NotificationLog]:
        """Get recent notification logs across all bookings."""
        stmt = (
            select(NotificationLog)
            .order_by(desc(NotificationLog.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
