"""Attempt-fenced, disposable speech previews; immutable transcripts stay separate."""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('speech_windows', sa.Column('preview', sa.Text(), nullable=False, server_default=''))
    op.add_column('speech_windows', sa.Column('preview_attempt', sa.String(36), nullable=False, server_default=''))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
