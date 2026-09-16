"""Immutable course hints pinned to future speech windows."""
from alembic import op
import sqlalchemy as sa

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('course_terminology',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('terms', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('course_id', 'version'),
        sa.CheckConstraint('version > 0', name='terminology_version_positive'))
    op.create_index('ix_course_terminology_course_id', 'course_terminology', ['course_id'])
    op.add_column('speech_windows', sa.Column('terminology', sa.JSON(), nullable=False, server_default='{}'))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
