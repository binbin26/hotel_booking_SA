"""Add requested_check_in and requested_check_out to bookings.

Revision ID: h0i1j2k3l4m5
Revises: g8h9i0j1k2l3
Create Date: 2026-06-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h0i1j2k3l4m5"
down_revision: Union[str, None] = "g8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add requested_check_in and requested_check_out columns to bookings table."""
    op.add_column(
        "bookings",
        sa.Column("requested_check_in", sa.Date(), nullable=True),
    )
    op.add_column(
        "bookings",
        sa.Column("requested_check_out", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    """Remove requested_check_in and requested_check_out columns from bookings table."""
    op.drop_column("bookings", "requested_check_out")
    op.drop_column("bookings", "requested_check_in")
