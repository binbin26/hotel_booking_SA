"""Add cancel_reason and cancelled_by to bookings.

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2026-06-09 16:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "g8h9i0j1k2l3"
down_revision = "f7g8h9i0j1k2"
branch_labels = None
depends_on = None

cancelled_by_enum = sa.Enum("ADMIN", "CUSTOMER", name="cancelled_by")


def upgrade() -> None:
    cancelled_by_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("bookings", sa.Column("cancel_reason", sa.Text(), nullable=True))
    op.add_column(
        "bookings",
        sa.Column("cancelled_by", cancelled_by_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bookings", "cancelled_by")
    op.drop_column("bookings", "cancel_reason")
    cancelled_by_enum.drop(op.get_bind(), checkfirst=True)
