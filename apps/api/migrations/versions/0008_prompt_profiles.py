"""Reusable local prompt profiles; no change to historical lecture settings."""
from alembic import op
import sqlalchemy as sa
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('prompt_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('detail_prompt', sa.String(2000), nullable=False),
        sa.Column('layout_prompt', sa.String(2000), nullable=False),
        sa.Column('instructions', sa.String(1000), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False))
    op.create_index('ix_prompt_profiles_owner_id', 'prompt_profiles', ['owner_id'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
