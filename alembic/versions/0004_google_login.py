"""sign in with Google: users.google_sub

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('google_sub', sa.String(length=64), nullable=True))
        batch.create_unique_constraint('uq_users_google_sub', ['google_sub'])


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('uq_users_google_sub', type_='unique')
        batch.drop_column('google_sub')
