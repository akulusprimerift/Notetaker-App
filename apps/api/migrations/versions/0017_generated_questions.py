"""Pinned generated study sets and protected question/quality revisions."""
from alembic import op
import sqlalchemy as sa

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('question_sets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lecture_id', sa.String(36), sa.ForeignKey('lectures.id'), nullable=False),
        sa.Column('preference_id', sa.String(36), sa.ForeignKey('note_preferences.id'), nullable=False),
        sa.Column('settings_id', sa.String(36), sa.ForeignKey('settings_versions.id'), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('preview', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('id', 'lecture_id'))
    op.create_index('ix_question_sets_lecture_id', 'question_sets', ['lecture_id'])
    op.create_table('question_edits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lecture_id', sa.String(36), nullable=False),
        sa.Column('set_id', sa.String(36), nullable=False),
        sa.Column('question_id', sa.String(16), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('quality', sa.JSON(), nullable=False),
        sa.Column('feedback', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['set_id', 'lecture_id'], ['question_sets.id', 'question_sets.lecture_id']),
        sa.UniqueConstraint('set_id', 'question_id', 'version'),
        sa.CheckConstraint('version > 0', name='question_edit_version'))
    op.create_index('ix_question_edits_lecture_id', 'question_edits', ['lecture_id'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
