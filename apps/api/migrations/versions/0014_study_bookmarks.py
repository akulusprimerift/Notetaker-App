"""Student timeline marks, separate from immutable source and note history."""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('important_marks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lecture_id', sa.String(36), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('sample', sa.BigInteger(), nullable=False),
        sa.Column('label', sa.String(160), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('removed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id', 'lecture_id'], ['capture_runs.id', 'capture_runs.lecture_id']),
        sa.CheckConstraint('sample >= 0 AND version > 0', name='important_mark_bounds'))
    op.create_index('ix_important_marks_lecture_id', 'important_marks', ['lecture_id'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
