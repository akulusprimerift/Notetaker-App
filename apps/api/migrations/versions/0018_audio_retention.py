"""Per-lecture audio retention and per-run released (transcribed and deleted) audio frontier, finalization audio choice."""
from alembic import op
import sqlalchemy as sa

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade():
    # Existing lectures keep their audio; new lectures choose explicitly (model default: False).
    op.add_column('lectures', sa.Column('keep_audio', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('capture_runs', sa.Column('released_through', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('finalizations', sa.Column('discard_audio', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
