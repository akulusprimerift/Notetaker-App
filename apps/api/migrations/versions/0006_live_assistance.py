"""Live windows, snapshot stability and custom note profiles; additive upgrade."""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('detail_prompt', 'layout_prompt'):
        op.add_column('settings_versions', sa.Column(name, sa.String(2000), nullable=False, server_default=''))
    op.add_column('speech_windows', sa.Column('live', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('transcript_snapshots', sa.Column('stability', sa.String(20), nullable=False, server_default='stable'))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
