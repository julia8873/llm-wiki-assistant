"""add is_teacher

Revision ID: 6a8d7211abcd
Revises: e99a6b82f5e9
Create Date: 2026-07-31 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a8d7211abcd'
down_revision: Union[str, None] = 'e99a6b82f5e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mapeos', sa.Column('is_teacher', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('mapeos', 'is_teacher')
