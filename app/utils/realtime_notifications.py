"""Real-time notification system using Server-Sent Events (SSE)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Global registry of active SSE connections (admin_id -> queue)
_admin_notification_queues: dict[int, asyncio.Queue] = {}


class NotificationEvent:
    """Represents a real-time notification event."""

    def __init__(
        self,
        event_type: str,
        booking_id: int,
        guest_name: str,
        message: str,
        action: str = "",
        extra_data: dict | None = None,
    ):
        self.event_type = event_type  # "invoice_interaction", "booking_created", etc
        self.booking_id = booking_id
        self.guest_name = guest_name
        self.message = message
        self.action = action  # "track", "edit", "cancel", etc
        self.timestamp = datetime.utcnow().isoformat()
        self.extra_data = extra_data or {}  # Additional metadata

    def to_sse_format(self) -> str:
        """Convert event to Server-Sent Events format."""
        data = {
            "type": self.event_type,
            "booking_id": self.booking_id,
            "guest_name": self.guest_name,
            "message": self.message,
            "action": self.action,
            "timestamp": self.timestamp,
        }
        # Include extra data if provided
        data.update(self.extra_data)
        return f"data: {json.dumps(data)}\n\n"


def register_admin_connection(admin_id: int) -> asyncio.Queue:
    """Register a new admin connection and return its notification queue."""
    queue = asyncio.Queue()
    _admin_notification_queues[admin_id] = queue
    logger.info("admin_sse_connection_opened", extra={"admin_id": admin_id})
    return queue


def unregister_admin_connection(admin_id: int) -> None:
    """Unregister an admin connection."""
    if admin_id in _admin_notification_queues:
        del _admin_notification_queues[admin_id]
        logger.info("admin_sse_connection_closed", extra={"admin_id": admin_id})


async def broadcast_notification(notification: NotificationEvent) -> None:
    """Broadcast a notification to all connected admins."""
    if not _admin_notification_queues:
        logger.debug("notification_skipped_no_connections", extra={"event": notification.event_type})
        return

    # Broadcast to all active admin connections
    for admin_id, queue in _admin_notification_queues.items():
        try:
            await asyncio.wait_for(queue.put(notification), timeout=1.0)
        except asyncio.TimeoutError:
            logger.warning(
                "notification_broadcast_timeout",
                extra={"admin_id": admin_id, "event": notification.event_type},
            )
        except Exception:
            logger.exception(
                "notification_broadcast_failed",
                extra={"admin_id": admin_id, "event": notification.event_type},
            )


async def notification_stream(admin_id: int) -> AsyncGenerator[str, None]:
    """Generate SSE events for an admin connection."""
    queue = register_admin_connection(admin_id)

    try:
        while True:
            try:
                notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield notification.to_sse_format()
            except asyncio.TimeoutError:
                # Send heartbeat comment to keep connection alive
                yield ": heartbeat\n\n"
            except asyncio.CancelledError:
                logger.info("admin_stream_cancelled", extra={"admin_id": admin_id})
                break
    finally:
        unregister_admin_connection(admin_id)
