"""Course tombstones fence creation and preserve child deletion reconciliation."""
from alembic import op
import sqlalchemy as sa
revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('courses', sa.Column('tombstoned', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
