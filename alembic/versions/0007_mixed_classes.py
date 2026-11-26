"""ห้องคละ: classrooms.mixed_classes, home_class on roster and submissions,
uniqueness by classroom + home class + number

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('classrooms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mixed_classes', sa.Boolean(), server_default=sa.false(), nullable=False))
    for table, old, new in (
        ('roster_entries', 'uq_roster_no', 'uq_roster_class_no'),
        ('submissions', 'uq_submission_no', 'uq_submission_class_no'),
    ):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('home_class', sa.String(length=20), server_default='', nullable=False))
        with op.batch_alter_table(table, schema=None) as batch_op:
            # New key first: on MySQL the old unique index must not be the last index on classroom_id.
            batch_op.create_unique_constraint(new, ['classroom_id', 'home_class', 'student_no'])
            batch_op.drop_constraint(old, type_='unique')


def downgrade() -> None:
    for table, old, new in (
        ('roster_entries', 'uq_roster_no', 'uq_roster_class_no'),
        ('submissions', 'uq_submission_no', 'uq_submission_class_no'),
    ):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_unique_constraint(old, ['classroom_id', 'student_no'])
            batch_op.drop_constraint(new, type_='unique')
            batch_op.drop_column('home_class')
    with op.batch_alter_table('classrooms', schema=None) as batch_op:
        batch_op.drop_column('mixed_classes')
