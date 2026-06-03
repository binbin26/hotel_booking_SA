class RoomNotAvailableException(Exception):
    """Raised when a room cannot be booked for the selected date range."""

    def __init__(self, room_id: int) -> None:
        self.room_id = room_id
        super().__init__(f"Room {room_id} is not available")


class RoomNotFoundException(Exception):
    """Raised when a booking flow references a missing room."""

    def __init__(self, room_id: int) -> None:
        self.room_id = room_id
        super().__init__(f"Room {room_id} not found")


class BookingNotFoundException(Exception):
    """Raised when a booking detail request cannot find a visible booking."""

    def __init__(self, booking_id: int) -> None:
        self.booking_id = booking_id
        super().__init__(f"Booking {booking_id} not found")


class BookingAlreadyCancelledException(Exception):
    """Raised when a cancellation request targets an already cancelled booking."""

    def __init__(self, booking_id: int) -> None:
        self.booking_id = booking_id
        super().__init__(f"Booking {booking_id} is already cancelled")
