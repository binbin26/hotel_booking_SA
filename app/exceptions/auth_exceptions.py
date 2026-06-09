class InvalidCredentialsException(Exception):
    """Raised when admin login credentials are wrong or the account is inactive."""

    def __init__(self) -> None:
        super().__init__("Invalid username or password")


class AdminNotAuthenticatedException(Exception):
    """Raised when an admin session cookie is missing or invalid."""

    def __init__(self) -> None:
        super().__init__("Admin authentication required")


class AdminNotFoundException(Exception):
    """Raised when a token references an admin account that no longer exists."""

    def __init__(self, admin_id: int) -> None:
        self.admin_id = admin_id
        super().__init__(f"Admin user {admin_id} not found")
