from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """Return the authenticated user (for JWT verification in Postman)."""
    return {
        "success": True,
        "message": "Authenticated",
        "data": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "role": current_user.role.value,
        },
    }


@router.get("/admin-check")
async def admin_check(current_user: User = Depends(require_admin)) -> dict:
    """Verify ADMIN-only access (for Postman role testing)."""
    return {
        "success": True,
        "message": "Admin access granted",
        "data": {"id": current_user.id, "role": current_user.role.value},
    }
