"""Merge multiple heads

Revision ID: 7b788e7c075d
Revises: d5b52dff3614, h0i1j2k3l4m5
Create Date: 2026-06-09 23:24:35.165834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b788e7c075d'
down_revision: Union[str, None] = ('d5b52dff3614', 'h0i1j2k3l4m5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
