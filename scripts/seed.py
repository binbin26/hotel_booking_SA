"""Standalone seed script for rooms and sample users (idempotent)."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import Room, RoomImage, User  # noqa: E402
from app.models.room import RoomStatus, RoomType  # noqa: E402
from app.models.user import UserRole  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROOMS_SEED: list[dict] = [
    # STANDARD x5 — A101–A105
    {"room_number": "A101", "room_type": RoomType.STANDARD, "capacity": 2, "price_per_night": Decimal("450000"), "description": "Standard room with garden view", "status": RoomStatus.AVAILABLE},
    {"room_number": "A102", "room_type": RoomType.STANDARD, "capacity": 2, "price_per_night": Decimal("475000"), "description": "Standard room floor 1", "status": RoomStatus.AVAILABLE},
    {"room_number": "A103", "room_type": RoomType.STANDARD, "capacity": 2, "price_per_night": Decimal("500000"), "description": "Standard room near elevator", "status": RoomStatus.AVAILABLE},
    {"room_number": "A104", "room_type": RoomType.STANDARD, "capacity": 2, "price_per_night": Decimal("525000"), "description": "Standard corner room", "status": RoomStatus.AVAILABLE},
    {"room_number": "A105", "room_type": RoomType.STANDARD, "capacity": 2, "price_per_night": Decimal("550000"), "description": "Standard room under maintenance", "status": RoomStatus.MAINTENANCE},
    # DELUXE x4 — B201–B204
    {"room_number": "B201", "room_type": RoomType.DELUXE, "capacity": 2, "price_per_night": Decimal("600000"), "description": "Deluxe room pool view", "status": RoomStatus.BOOKED},
    {"room_number": "B202", "room_type": RoomType.DELUXE, "capacity": 2, "price_per_night": Decimal("650000"), "description": "Deluxe room with balcony", "status": RoomStatus.BOOKED},
    {"room_number": "B203", "room_type": RoomType.DELUXE, "capacity": 2, "price_per_night": Decimal("675000"), "description": "Deluxe corner room", "status": RoomStatus.AVAILABLE},
    {"room_number": "B204", "room_type": RoomType.DELUXE, "capacity": 2, "price_per_night": Decimal("700000"), "description": "Deluxe high-floor room", "status": RoomStatus.AVAILABLE},
    # SUITE x4 — C301–C304
    {"room_number": "C301", "room_type": RoomType.SUITE, "capacity": 3, "price_per_night": Decimal("900000"), "description": "Suite with living area", "status": RoomStatus.AVAILABLE},
    {"room_number": "C302", "room_type": RoomType.SUITE, "capacity": 3, "price_per_night": Decimal("950000"), "description": "Suite corner panoramic view", "status": RoomStatus.AVAILABLE},
    {"room_number": "C303", "room_type": RoomType.SUITE, "capacity": 3, "price_per_night": Decimal("1000000"), "description": "Executive suite", "status": RoomStatus.AVAILABLE},
    {"room_number": "C304", "room_type": RoomType.SUITE, "capacity": 3, "price_per_night": Decimal("1100000"), "description": "Premium suite", "status": RoomStatus.AVAILABLE},
    # VIP x2 — D401–D402
    {"room_number": "D401", "room_type": RoomType.VIP, "capacity": 4, "price_per_night": Decimal("1500000"), "description": "VIP suite presidential floor", "status": RoomStatus.AVAILABLE},
    {"room_number": "D402", "room_type": RoomType.VIP, "capacity": 4, "price_per_night": Decimal("2000000"), "description": "VIP penthouse suite", "status": RoomStatus.AVAILABLE},
]

USERS_SEED: list[dict] = [
    {
        "full_name": "Hotel Admin",
        "email": "admin@hotel.com",
        "phone": "0901000001",
        "password": "admin123",
        "role": UserRole.ADMIN,
    },
    {
        "full_name": "Sample Guest",
        "email": "guest@hotel.com",
        "phone": "0901000002",
        "password": "guest123",
        "role": UserRole.GUEST,
    },
]


ROOM_IMAGES_SEED: dict[str, list[dict]] = {
    "A101": [
        {
            "image_url": "https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1600&q=80",
            "is_primary": True,
        },
        {
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1600&q=80",
            "is_primary": False,
        },
    ],
    "B201": [
        {
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1600&q=80",
            "is_primary": True,
        },
    ],
}


async def seed_room_images(session) -> int:
    """Insert sample images for seeded rooms (by room_number). Returns count inserted."""
    inserted = 0
    for room_number, images in ROOM_IMAGES_SEED.items():
        room_id = await session.scalar(
            select(Room.id).where(Room.room_number == room_number)
        )
        if room_id is None:
            continue
        for image in images:
            exists = await session.scalar(
                select(RoomImage.id).where(
                    RoomImage.room_id == room_id,
                    RoomImage.image_url == image["image_url"],
                )
            )
            if exists:
                continue
            session.add(RoomImage(room_id=room_id, **image))
            inserted += 1
    return inserted


async def seed_rooms(session) -> int:
    """Insert rooms that do not yet exist (by room_number). Returns count inserted."""
    inserted = 0
    for data in ROOMS_SEED:
        exists = await session.scalar(
            select(Room.id).where(Room.room_number == data["room_number"])
        )
        if exists:
            continue
        session.add(Room(**data))
        inserted += 1
    return inserted


async def seed_users(session) -> int:
    """Insert users that do not yet exist (by email). Returns count inserted."""
    inserted = 0
    for data in USERS_SEED:
        exists = await session.scalar(select(User.id).where(User.email == data["email"]))
        if exists:
            continue
        session.add(
            User(
                full_name=data["full_name"],
                email=data["email"],
                phone=data["phone"],
                password_hash=pwd_context.hash(data["password"]),
                role=data["role"],
            )
        )
        inserted += 1
    return inserted


async def main() -> None:
    """Run idempotent seed for rooms and users."""
    async with AsyncSessionLocal() as session:
        await seed_rooms(session)
        await seed_users(session)
        await seed_room_images(session)
        await session.commit()

    print("✓ Seeded 15 rooms, 2 users, sample room images")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
