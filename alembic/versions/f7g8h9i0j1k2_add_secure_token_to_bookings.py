"""Add secure_token to bookings for guest self-service links.

Revision ID: f7g8h9i0j1k2
Revises: e1f2g3h4i5j6
Create Date: 2026-06-09 14:00:00.000000

"""
import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f7g8h9i0j1k2"
down_revision = "e1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("secure_token", sa.String(length=64), nullable=True),
    )

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM bookings WHERE secure_token IS NULL"))
    for row in rows:
        connection.execute(
            sa.text("UPDATE bookings SET secure_token = :token WHERE id = :id"),
            {"token": uuid.uuid4().hex, "id": row.id},
        )

    op.alter_column("bookings", "secure_token", existing_type=sa.String(64), nullable=False)
    op.create_unique_constraint("uq_bookings_secure_token", "bookings", ["secure_token"])


def downgrade() -> None:
    op.drop_constraint("uq_bookings_secure_token", "bookings", type_="unique")
    op.drop_column("bookings", "secure_token")
