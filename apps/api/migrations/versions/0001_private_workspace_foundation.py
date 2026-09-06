"""private workspace foundation

Revision ID: 0001
Revises: none
Create Date: 2026-09-06 12:06:38.395121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Frozen initial schema; later changes belong in new revisions.
    op.create_table('bootstrap_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('id = 1', name='one_bootstrap'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('inbox_events',
    sa.Column('consumer', sa.String(length=60), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('processed_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('consumer', 'event_id')
    )
    op.create_table('owners',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('singleton', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('singleton = 1', name='one_local_owner'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('singleton')
    )
    op.create_table('command_receipts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('action', sa.String(length=120), nullable=False),
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('result_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('owner_id', 'action', 'key')
    )
    op.create_table('courses',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('code', sa.String(length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'owner_id')
    )
    op.create_index(op.f('ix_courses_owner_id'), 'courses', ['owner_id'], unique=False)
    op.create_table('sessions',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('csrf_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ),
    sa.PrimaryKeyConstraint('token_hash')
    )
    op.create_table('lectures',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('course_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('lifecycle_epoch', sa.Integer(), nullable=False),
    sa.Column('capture_epoch', sa.Integer(), nullable=False),
    sa.Column('audio_epoch', sa.Integer(), nullable=False),
    sa.Column('update_seq', sa.Integer(), nullable=False),
    sa.Column('tombstoned', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lectures_course_id'), 'lectures', ['course_id'], unique=False)
    op.create_table('jobs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('logical_key', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('lifecycle_epoch', sa.Integer(), nullable=False),
    sa.Column('audio_epoch', sa.Integer(), nullable=True),
    sa.Column('input_revision', sa.String(length=80), nullable=False),
    sa.Column('due_at', sa.DateTime(), nullable=False),
    sa.Column('attempt_token', sa.String(length=36), nullable=True),
    sa.Column('lease_expires_at', sa.DateTime(), nullable=True),
    sa.Column('error_code', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('logical_key')
    )
    op.create_index(op.f('ix_jobs_due_at'), 'jobs', ['due_at'], unique=False)
    op.create_index(op.f('ix_jobs_lecture_id'), 'jobs', ['lecture_id'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_table('lecture_updates',
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.String(length=36), nullable=False),
    sa.Column('entity_version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ),
    sa.PrimaryKeyConstraint('lecture_id', 'sequence')
    )
    op.create_table('outbox_events',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('event_type', sa.String(length=60), nullable=False),
    sa.Column('schema_version', sa.Integer(), nullable=False),
    sa.Column('entity_id', sa.String(length=36), nullable=False),
    sa.Column('lifecycle_epoch', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outbox_events_published_at'), 'outbox_events', ['published_at'], unique=False)
    op.create_table('settings_versions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('depth', sa.String(length=20), nullable=False),
    sa.Column('format', sa.String(length=24), nullable=False),
    sa.Column('ai_explanations', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('lecture_id', 'version')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Preserve user data; use a reviewed forward fix or isolated backup restore."""
    raise RuntimeError("Destructive downgrade is disabled. Restore a verified backup in isolation or apply a forward migration.")
