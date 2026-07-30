"""baseline

Revision ID: 0001
Revises: 
Create Date: 2024-05-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('mapeos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('moodle_user_id', sa.Integer(), nullable=False),
    sa.Column('moodle_course_id', sa.Integer(), nullable=False),
    sa.Column('repo_url', sa.String(), nullable=True),
    sa.Column('git_provider', sa.String(), nullable=False, server_default='github'),
    sa.Column('matrix_room_id', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('moodle_user_id', 'moodle_course_id', name='uq_user_course')
    )
    op.create_index(op.f('ix_mapeos_id'), 'mapeos', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mapeos_id'), table_name='mapeos')
    op.drop_table('mapeos')
