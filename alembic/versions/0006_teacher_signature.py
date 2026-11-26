"""teacher_signatures: signature image printed on the memo and individual records

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('teacher_signatures',
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.LargeBinary(length=16777215), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('teacher_id')
    )


def downgrade() -> None:
    op.drop_table('teacher_signatures')
