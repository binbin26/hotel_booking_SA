"""create_users_rooms_bookings

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-05-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("GUEST", "ADMIN", name="user_role"),
            server_default="GUEST",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_number", sa.String(length=10), nullable=False),
        sa.Column(
            "room_type",
            sa.Enum("STANDARD", "DELUXE", "SUITE", "VIP", name="room_type"),
            nullable=False,
        ),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("price_per_night", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("AVAILABLE", "BOOKED", "MAINTENANCE", name="room_status"),
            server_default="AVAILABLE",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_number"),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column("total_nights", sa.Integer(), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "CONFIRMED", "CANCELLED", name="booking_status"),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            sa.Enum("CASH", "MOMO", "ZALOPAY", "BANKING", name="payment_method"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bookings_room_dates",
        "bookings",
        ["room_id", "check_in", "check_out"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_room_dates", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("rooms")
    op.drop_table("users")
