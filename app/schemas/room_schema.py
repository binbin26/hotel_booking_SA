from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoomImageResponse(BaseModel):
    """Single room image in detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    is_primary: bool


class RoomDetailResponse(BaseModel):
    """Public room detail including gallery images."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: str
    capacity: int = Field(..., gt=0)
    price_per_night: Decimal
    description: Optional[str] = None
    status: str
    images: list[RoomImageResponse] = Field(default_factory=list)
