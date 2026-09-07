"""generated study notes

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-07 16:54:13.080520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('note_preferences',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('model', sa.String(length=160), nullable=False),
    sa.Column('model_digest', sa.String(length=64), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'lecture_id'),
    sa.UniqueConstraint('lecture_id', 'version')
    )
    op.create_index(op.f('ix_note_preferences_lecture_id'), 'note_preferences', ['lecture_id'], unique=False)
    op.create_table('note_requests',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('preference_id', sa.String(length=36), nullable=False),
    sa.Column('snapshot_id', sa.String(length=36), nullable=False),
    sa.Column('settings_id', sa.String(length=36), nullable=False),
    sa.Column('base_revision', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['preference_id', 'lecture_id'], ['note_preferences.id', 'note_preferences.lecture_id'], ),
    sa.ForeignKeyConstraint(['settings_id'], ['settings_versions.id'], ),
    sa.ForeignKeyConstraint(['snapshot_id', 'lecture_id'], ['transcript_snapshots.id', 'transcript_snapshots.lecture_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'lecture_id'),
    sa.UniqueConstraint('snapshot_id', 'preference_id', 'settings_id')
    )
    op.create_index(op.f('ix_note_requests_lecture_id'), 'note_requests', ['lecture_id'], unique=False)
    op.create_table('note_revisions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('lecture_id', sa.String(length=36), nullable=False),
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('attempt_token', sa.String(length=36), nullable=False),
    sa.Column('content', sa.JSON(), nullable=False),
    sa.Column('resolved_citations', sa.JSON(), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['request_id', 'lecture_id'], ['note_requests.id', 'note_requests.lecture_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('attempt_token'),
    sa.UniqueConstraint('lecture_id', 'revision'),
    sa.UniqueConstraint('request_id')
    )
    op.create_index(op.f('ix_note_revisions_lecture_id'), 'note_revisions', ['lecture_id'], unique=False)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade refused. Restore a verified backup instead.")
