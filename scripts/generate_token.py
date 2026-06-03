"""Generate a JWT access token for Postman testing (no login endpoint required)."""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.security import create_access_token  # noqa: E402
from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.auth_schema import UserRole  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate JWT for Postman testing")
    parser.add_argument(
        "--email",
        default="guest@hotel.com",
        help="User email (default: guest@hotel.com)",
    )
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == args.email))
        if user is None:
            print(f"User not found: {args.email}. Run: python scripts/seed.py")
            sys.exit(1)

        token = create_access_token(
            subject=user.id,
            role=UserRole(user.role.value),
        )

    print(f"User: {user.email} (id={user.id}, role={user.role.value})")
    print(f"\nBearer token:\n{token}")
    print("\nPostman header:")
    print(f"Authorization: Bearer {token}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
