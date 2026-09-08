"""Durable final snapshots and restartable deletion inventory."""
from alembic import op
import sqlalchemy as sa
revision='0009'
down_revision='0008'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('lectures',sa.Column('audio_removed',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_table('finalizations',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('lecture_id',sa.String(36),sa.ForeignKey('lectures.id'),nullable=False),
        sa.Column('lifecycle_epoch',sa.Integer(),nullable=False),
        sa.Column('audio_epoch',sa.Integer(),nullable=False),
        sa.Column('expected_edit_version',sa.Integer(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('issues',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_finalizations_lecture_id','finalizations',['lecture_id'])
    op.create_table('final_snapshots',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('lecture_id',sa.String(36),sa.ForeignKey('lectures.id'),nullable=False),
        sa.Column('finalization_id',sa.String(36),sa.ForeignKey('finalizations.id'),nullable=False,unique=True),
        sa.Column('content',sa.JSON(),nullable=False),
        sa.Column('markdown',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_final_snapshots_lecture_id','final_snapshots',['lecture_id'])
    op.create_table('deletions',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('lecture_id',sa.String(36),sa.ForeignKey('lectures.id'),nullable=False),
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),nullable=False),
        sa.Column('kind',sa.String(16),nullable=False),
        sa.Column('lifecycle_epoch',sa.Integer(),nullable=False),
        sa.Column('audio_epoch',sa.Integer(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),
        sa.Column('error',sa.String(100)),
        sa.Column('browser_ack',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False),
        sa.Column('reconciled_at',sa.DateTime()))
    op.create_index('ix_deletions_lecture_id','deletions',['lecture_id'])
    op.create_index('ix_deletions_owner_id','deletions',['owner_id'])
    op.create_table('deletion_objects',
        sa.Column('deletion_id',sa.String(36),sa.ForeignKey('deletions.id'),primary_key=True),
        sa.Column('object_key',sa.String(240),primary_key=True),
        sa.Column('removed',sa.Boolean(),nullable=False))


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
