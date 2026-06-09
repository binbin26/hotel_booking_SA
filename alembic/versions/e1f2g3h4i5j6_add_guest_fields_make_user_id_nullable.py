"""Add guest fields and make user_id nullable.

Revision ID: e1f2g3h4i5j6
Revises: d4e5f6a7b8c9
Create Date: 2026-06-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new guest columns to bookings table
    op.add_column('bookings', sa.Column('guest_name', sa.String(255), nullable=False, server_default=''))
    op.add_column('bookings', sa.Column('guest_email', sa.String(255), nullable=False, server_default=''))
    op.add_column('bookings', sa.Column('guest_phone', sa.String(20), nullable=True))
    
    # Make user_id nullable
    op.alter_column(
        'bookings',
        'user_id',
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Make user_id required again
    op.alter_column(
        'bookings',
        'user_id',
        existing_type=sa.Integer(),
        nullable=False,
    )
    
    # Remove guest columns
    op.drop_column('bookings', 'guest_name')
    op.drop_column('bookings', 'guest_email')
    op.drop_column('bookings', 'guest_phone')
