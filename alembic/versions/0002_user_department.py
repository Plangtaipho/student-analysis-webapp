"""teacher department (กลุ่มงาน) for the memo's ส่วนราชการ line

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('department', sa.String(length=120), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('users', 'department')
