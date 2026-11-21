"""users.learning_area: กลุ่มสาระ kept apart from กลุ่มงาน

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

WORK_GROUPS = ("กลุ่มบริหารวิชาการ", "กลุ่มบริหารงบประมาณ", "กลุ่มบริหารงานบุคคล", "กลุ่มบริหารงานทั่วไป")


def upgrade() -> None:
    op.add_column('users', sa.Column('learning_area', sa.String(length=120), nullable=False, server_default=''))
    users = sa.table('users', sa.column('department', sa.String), sa.column('learning_area', sa.String))
    # Earlier sign-ups could type a กลุ่มสาระ into the กลุ่มงาน box: move it to the new column
    # and leave กลุ่มงาน empty so the teacher is asked to pick one before the next memo.
    op.execute(
        users.update()
        .where(sa.and_(users.c.department != '', users.c.department.notin_(WORK_GROUPS)))
        .values(learning_area=users.c.department, department='')
    )


def downgrade() -> None:
    op.drop_column('users', 'learning_area')
