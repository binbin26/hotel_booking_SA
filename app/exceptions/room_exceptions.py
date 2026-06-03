class RoomNotFoundException(Exception):
    """Raised when a room id does not exist."""

    def __init__(self, room_id: int) -> None:
        self.room_id = room_id
        super().__init__(f"Room {room_id} not found")
