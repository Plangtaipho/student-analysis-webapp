"""payments: reject reason, upload time, slip images in the database

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reject_reason', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('submitted_at', sa.DateTime(), nullable=True))
    op.create_table('payment_slips',
    sa.Column('subscription_id', sa.Integer(), nullable=False),
    sa.Column('mime', sa.String(length=40), nullable=False),
    sa.Column('data', sa.LargeBinary(length=16777215), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('subscription_id')
    )


def downgrade() -> None:
    op.drop_table('payment_slips')
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('submitted_at')
        batch_op.drop_column('reject_reason')
