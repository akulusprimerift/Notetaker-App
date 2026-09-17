"""Revision-scoped, append-only learning self-assessments."""
from alembic import op
import sqlalchemy as sa

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('learning_reviews',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lecture_id', sa.String(36), sa.ForeignKey('lectures.id'), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('block_id', sa.String(160), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('rating', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('lecture_id', 'revision_id', 'block_id', 'version'),
        sa.CheckConstraint("version > 0 AND rating IN ('again', 'developing', 'confident', 'unreviewed')", name='learning_review_bounds'))
    op.create_index('ix_learning_reviews_lecture_id', 'learning_reviews', ['lecture_id'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
