import enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class UserRole(str, enum.Enum):
    """Application user roles aligned with the users.role column."""

    GUEST = "GUEST"
    ADMIN = "ADMIN"


class TokenPayload(BaseModel):
    """Claims extracted from a validated JWT access token."""

    sub: Annotated[int, Field(description="User ID")]
    role: UserRole
    exp: int

    @field_validator("sub", mode="before")
    @classmethod
    def parse_subject(cls, value: str | int) -> int:
        """JWT subject claim is stored as a string but represents user id."""
        return int(value)
