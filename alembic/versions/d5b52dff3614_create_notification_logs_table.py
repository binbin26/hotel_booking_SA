"""create_notification_logs_table

Revision ID: d5b52dff3614
Revises: g8h9i0j1k2l3
Create Date: 2026-06-09 22:12:49.162886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5b52dff3614'
down_revision: Union[str, None] = 'g8h9i0j1k2l3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Không làm gì cả vì Alembic quét nhầm lệnh xóa cấu trúc cũ
    pass

def downgrade() -> None:
    pass
