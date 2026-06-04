from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


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


class RoomUpdate(BaseModel):
    """Request schema for admin room updates."""

    room_type: str
    capacity: int = Field(..., gt=0)
    price_per_night: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    status: str


class RoomUpdateResponse(BaseModel):
    """Response schema for room updates."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: str
    capacity: int
    price_per_night: Decimal
    description: Optional[str] = None
    status: str


class RoomSearchResponse(BaseModel):
    """Response schema for room search availability."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: str
    capacity: int = Field(..., gt=0)
    price_per_night: Decimal
    total_nights: int
    estimated_total_price: Decimal
    status: str

    @field_serializer("estimated_total_price")
    def serialize_estimated_total_price(
        self, value: Decimal
    ) -> int | float:
        """Render whole-number prices as JSON numbers."""
        if value == value.to_integral_value():
            return int(value)
        return float(value)
