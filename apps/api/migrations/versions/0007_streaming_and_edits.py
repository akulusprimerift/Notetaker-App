"""Recoverable generation preview and immutable student note revisions."""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('note_requests', sa.Column('preview', sa.Text(), nullable=False, server_default=''))
    op.add_column('note_requests', sa.Column('preview_attempt', sa.String(36), nullable=False, server_default=''))
    op.create_table('note_edits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lecture_id', sa.String(36), sa.ForeignKey('lectures.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('generated_id', sa.String(36), sa.ForeignKey('note_revisions.id'), nullable=False),
        sa.Column('reviewed_id', sa.String(36), sa.ForeignKey('note_revisions.id'), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('lecture_id', 'version'))
    op.create_index('ix_note_edits_lecture_id', 'note_edits', ['lecture_id'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
