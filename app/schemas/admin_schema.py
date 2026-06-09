from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminLoginRequest(BaseModel):
    """Credentials submitted on the admin login form."""

    username: Annotated[str, Field(min_length=1, max_length=50)]
    password: Annotated[str, Field(min_length=1)]


class AdminUserResponse(BaseModel):
    """Public admin account fields returned after authentication."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool


class AdminLoginResponse(BaseModel):
    """Successful admin authentication payload."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    admin: AdminUserResponse


class AdminTokenPayload(BaseModel):
    """Claims extracted from a validated admin JWT."""

    sub: Annotated[int, Field(description="Admin user ID")]
    token_type: Literal["admin"]
    exp: int

    @field_validator("sub", mode="before")
    @classmethod
    def parse_subject(cls, value: str | int) -> int:
        """JWT subject claim is stored as a string but represents admin id."""
        return int(value)
