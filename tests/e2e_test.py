from playwright.sync_api import sync_playwright
from sqlalchemy import select
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.security import create_access_token
from app.database import AsyncSessionLocal
from app.models.user import User
from app.schemas.auth_schema import UserRole

BASE_URL = "http://127.0.0.1:8000"


async def get_admin_token():
    async with AsyncSessionLocal() as session:
        user = await session.scalar(
            select(User).where(User.email == "admin@hotel.com")
        )

        if not user:
            raise Exception("admin@hotel.com not found")

        token = create_access_token(
            subject=user.id,
            role=UserRole(user.role.value)
        )

        return token


def test_integration():
    token = asyncio.run(get_admin_token())

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500
        )

        page = browser.new_page()

        print("\n==============================")
        print("D1 - GUEST FLOW")
        print("==============================\n")

        print("1. Search Room")

        search = page.request.get(
            f"{BASE_URL}/rooms/search",
            params={
                "check_in": "2026-06-20",
                "check_out": "2026-06-22",
                "guests": 2
            }
        )

        assert search.ok, search.text()

        rooms = search.json()
        room_id = rooms["data"][0]["id"]

        print(f"PASS - Room ID: {room_id}")

        page.goto(f"{BASE_URL}/docs")
        page.screenshot(path="screenshots/01-search-room.png")

        print("\n2. Create Booking")

        booking = page.request.post(
            f"{BASE_URL}/bookings",
            headers=headers,
            data=json.dumps({
                "user_id": 1,
                "room_id": room_id,
                "check_in": "2026-06-20",
                "check_out": "2026-06-22",
                "payment_method": "MOMO"
            })
        )

        assert booking.ok, booking.text()

        booking_data = booking.json()

        booking_id = booking_data["data"]["booking_id"]

        total_price = booking_data["data"]["total_price"]

        print(f"PASS - Booking ID: {booking_id}")
        print(json.dumps(booking_data, indent=2))
        page.screenshot(path="screenshots/02-create-booking.png")

        print("\n3. Payment")

        payment = page.request.post(
            f"{BASE_URL}/bookings/{booking_id}/payment",
            headers=headers,
            data=json.dumps({
                "booking_id": booking_id,
                "amount": total_price,
                "payment_method": "MOMO"
            })
        )

        assert payment.ok, payment.text()

        print("PASS")
        page.screenshot(path="screenshots/03-payment.png")

        print("\n4. View Confirmation")

        detail = page.request.get(
            f"{BASE_URL}/bookings/{booking_id}",
            headers=headers
        )

        assert detail.ok, detail.text()

        booking_detail = detail.json()

        print(f"PASS - Status: {booking_detail['data']['status']}")
        page.screenshot(path="screenshots/04-booking-detail.png")

        print("\n==============================")
        print("D2 - ADMIN FLOW")
        print("==============================\n")

        print("5. Admin Login")

        auth = page.request.get(
            f"{BASE_URL}/auth/me",
            headers=headers
        )

        assert auth.ok, auth.text()

        auth_data = auth.json()

        print(f"PASS - Role: {auth_data['data']['role']}")
        page.screenshot(path="screenshots/05-admin-login.png")

        print("\n6. View Booking")

        view_booking = page.request.get(
            f"{BASE_URL}/bookings/{booking_id}",
            headers=headers
        )

        assert view_booking.ok, view_booking.text()

        print("PASS")
        page.screenshot(path="screenshots/06-admin-view-booking.png")

        print("\n7. Update Room")

        update_room = page.request.put(
            f"{BASE_URL}/admin/rooms/{room_id}",
            headers=headers,
            data=json.dumps({
                "room_type": "SUITE",
                "capacity": 4,
                "price_per_night": 900000,
                "status": "AVAILABLE"
            })
        )

        assert update_room.ok, update_room.text()

        print("PASS")
        page.screenshot(path="screenshots/07-admin-update-room.png")

        print("\n==============================")
        print("INTEGRATION TEST COMPLETED")
        print("==============================")

        browser.close()


if __name__ == "__main__":
    test_integration()