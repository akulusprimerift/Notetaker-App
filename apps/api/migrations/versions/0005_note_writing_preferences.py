"""Course-neutral note writing preferences."""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings_versions', sa.Column('instructions', sa.String(1000), nullable=False, server_default=''))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
