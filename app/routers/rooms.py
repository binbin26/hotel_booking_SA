from typing import Any
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_admin
from app.dependencies.room import get_room_service
from app.exceptions.room_exceptions import RoomNotFoundException
from app.models.user import User
from app.schemas.room_schema import RoomDetailResponse, RoomSearchResponse, RoomUpdate, RoomUpdateResponse
from app.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/search", response_model=None)
async def search_rooms(
    check_in: date,
    check_out: date,
    guests: int,
    room_service: RoomService = Depends(get_room_service),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: search available rooms by date range and guest count."""
    try:
        results = await room_service.search_available_rooms(
            check_in=check_in,
            check_out=check_out,
            capacity=guests,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(e),
                "error_code": "INVALID_DATE_RANGE",
            },
        )
    
    rooms_data = [
        {
            **RoomSearchResponse(
                id=room.id,
                room_number=room.room_number,
                room_type=room.room_type.value,
                capacity=room.capacity,
                price_per_night=room.price_per_night,
                total_nights=total_nights,
                estimated_total_price=estimated_price,
                status=room.status.value,
            ).model_dump(mode="json"),
        }
        for room, total_nights, estimated_price in results
    ]
    
    return {
        "success": True,
        "message": "Available rooms found",
        "data": rooms_data,
    }


@router.get("/{room_id}", response_model=None)
async def get_room_detail(
    room_id: int,
    room_service: RoomService = Depends(get_room_service),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: room detail with images."""
    try:
        room = await room_service.get_room_detail(room_id)
    except RoomNotFoundException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            },
        )

    return {
        "success": True,
        "message": "Room details retrieved",
        "data": RoomDetailResponse.model_validate(room).model_dump(mode="json"),
    }


@admin_router.put("/rooms/{room_id}", response_model=None)
async def update_room(
    room_id: int,
    body: RoomUpdate,
    room_service: RoomService = Depends(get_room_service),
    admin_user: User = Depends(require_admin),
) -> dict[str, Any] | JSONResponse:
    """Admin endpoint: update room details."""
    try:
        room = await room_service.update_room(
            room_id=room_id,
            room_type=body.room_type,
            capacity=body.capacity,
            price_per_night=body.price_per_night,
            description=body.description,
            status=body.status,
        )
    except RoomNotFoundException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            },
        )

    return {
        "success": True,
        "message": "Room updated successfully",
        "data": RoomUpdateResponse.model_validate(room).model_dump(mode="json"),
    }
