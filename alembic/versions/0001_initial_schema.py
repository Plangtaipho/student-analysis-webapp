"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('assessment_items',
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('domain_no', sa.SmallInteger(), nullable=False),
    sa.Column('domain_name', sa.String(length=120), nullable=False),
    sa.Column('item_no', sa.SmallInteger(), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('code')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=False),
    sa.Column('role', sa.Enum('teacher', 'admin', name='role', native_enum=False, length=16), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('position', sa.String(length=80), nullable=False),
    sa.Column('school_name', sa.String(length=160), nullable=False),
    sa.Column('area_office', sa.String(length=200), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('classrooms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('subject_name', sa.String(length=120), nullable=False),
    sa.Column('subject_code', sa.String(length=20), nullable=False),
    sa.Column('grade_label', sa.String(length=40), nullable=False),
    sa.Column('academic_year', sa.SmallInteger(), nullable=False),
    sa.Column('semester', sa.SmallInteger(), nullable=False),
    sa.Column('public_token', sa.String(length=32), nullable=False),
    sa.Column('is_open', sa.Boolean(), nullable=False),
    sa.Column('is_trial', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('classrooms', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_classrooms_public_token'), ['public_token'], unique=True)
        batch_op.create_index(batch_op.f('ix_classrooms_teacher_id'), ['teacher_id'], unique=False)

    op.create_table('subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('academic_year', sa.SmallInteger(), nullable=False),
    sa.Column('semester', sa.SmallInteger(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='subscriptionstatus', native_enum=False, length=16), nullable=False),
    sa.Column('slip_path', sa.String(length=255), nullable=False),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('teacher_id', 'academic_year', 'semester', name='uq_subscription_term')
    )
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_subscriptions_teacher_id'), ['teacher_id'], unique=False)

    op.create_table('roster_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('classroom_id', sa.Integer(), nullable=False),
    sa.Column('student_no', sa.SmallInteger(), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('classroom_id', 'student_no', name='uq_roster_no')
    )
    with op.batch_alter_table('roster_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_roster_entries_classroom_id'), ['classroom_id'], unique=False)

    op.create_table('submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('classroom_id', sa.Integer(), nullable=False),
    sa.Column('student_no', sa.SmallInteger(), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('nickname', sa.String(length=40), nullable=False),
    sa.Column('personal_info', sa.JSON(), nullable=False),
    sa.Column('open_answers', sa.JSON(), nullable=False),
    sa.Column('learning_prefs', sa.JSON(), nullable=False),
    sa.Column('consent_at', sa.DateTime(), nullable=True),
    sa.Column('edit_code_hash', sa.String(length=100), nullable=False),
    sa.Column('created_by_teacher', sa.Boolean(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('classroom_id', 'student_no', name='uq_submission_no')
    )
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_submissions_classroom_id'), ['classroom_id'], unique=False)

    op.create_table('evaluations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('submission_id', sa.Integer(), nullable=False),
    sa.Column('last_grade', sa.String(length=10), nullable=False),
    sa.Column('teacher_comment', sa.Text(), nullable=False),
    sa.Column('group_override', sa.Enum('high', 'medium', 'low', 'disability', name='learnergroup', native_enum=False, length=16), nullable=True),
    sa.Column('evaluated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('evaluations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_evaluations_submission_id'), ['submission_id'], unique=True)

    op.create_table('evaluation_scores',
    sa.Column('evaluation_id', sa.Integer(), nullable=False),
    sa.Column('item_code', sa.String(length=10), nullable=False),
    sa.Column('rating', sa.Enum('good', 'fair', 'improve', name='rating', native_enum=False, length=10), nullable=False),
    sa.Column('improvement_note', sa.String(length=200), nullable=False),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_code'], ['assessment_items.code'], ),
    sa.PrimaryKeyConstraint('evaluation_id', 'item_code')
    )

    # Seed the 16 assessment items of part 3 (fixed by the paper form).
    from app.services.form_definition import assessment_item_rows

    items = sa.table(
        "assessment_items",
        sa.column("code", sa.String),
        sa.column("domain_no", sa.SmallInteger),
        sa.column("domain_name", sa.String),
        sa.column("item_no", sa.SmallInteger),
        sa.column("label", sa.String),
        sa.column("sort_order", sa.SmallInteger),
    )
    op.bulk_insert(items, assessment_item_rows())


def downgrade() -> None:
    op.drop_table('evaluation_scores')
    with op.batch_alter_table('evaluations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_evaluations_submission_id'))

    op.drop_table('evaluations')
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_submissions_classroom_id'))

    op.drop_table('submissions')
    with op.batch_alter_table('roster_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_roster_entries_classroom_id'))

    op.drop_table('roster_entries')
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_subscriptions_teacher_id'))

    op.drop_table('subscriptions')
    with op.batch_alter_table('classrooms', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_classrooms_teacher_id'))
        batch_op.drop_index(batch_op.f('ix_classrooms_public_token'))

    op.drop_table('classrooms')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    op.drop_table('assessment_items')
