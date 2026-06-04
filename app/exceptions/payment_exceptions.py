class PaymentAlreadyPaidException(Exception):
    """Raised when attempting to pay an already confirmed booking."""

    def __init__(self, booking_id: int) -> None:
        self.booking_id = booking_id
        super().__init__(f"Booking {booking_id} is already paid")


class PaymentAmountMismatchException(Exception):
    """Raised when payment amount does not match booking total price."""

    def __init__(self, booking_id: int, expected: float, received: float) -> None:
        self.booking_id = booking_id
        self.expected = expected
        self.received = received
        super().__init__(
            f"Payment amount mismatch for booking {booking_id}: "
            f"expected {expected}, received {received}"
        )
