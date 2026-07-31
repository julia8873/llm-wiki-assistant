"""add official repo url

Revision ID: e99a6b82f5e9
Revises: 0001
Create Date: 2026-07-31 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e99a6b82f5e9'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        with op.batch_alter_table('mapeos') as batch_op:
            batch_op.add_column(sa.Column('official_repo_url', sa.String(), nullable=True))
    except Exception as e:
        # Ignore if column already exists
        pass


def downgrade() -> None:
    with op.batch_alter_table('mapeos') as batch_op:
        batch_op.drop_column('official_repo_url')
