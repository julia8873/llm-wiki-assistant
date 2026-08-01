"""add moodle_username

Revision ID: 4880f2b9ab35
Revises: 6a8d7211abcd
Create Date: 2026-08-01 07:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4880f2b9ab35'
down_revision: Union[str, None] = '6a8d7211abcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        with op.batch_alter_table('mapeos') as batch_op:
            batch_op.add_column(sa.Column('moodle_username', sa.String(), nullable=True))
    except Exception as e:
        pass


def downgrade() -> None:
    with op.batch_alter_table('mapeos') as batch_op:
        batch_op.drop_column('moodle_username')
