from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies.room import get_room_service
from app.exceptions.room_exceptions import RoomNotFoundException
from app.schemas.room_schema import RoomDetailResponse
from app.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/{room_id}", response_model=None)
async def get_room_detail(
    room_id: int,
    room_service: RoomService = Depends(get_room_service),
):
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
