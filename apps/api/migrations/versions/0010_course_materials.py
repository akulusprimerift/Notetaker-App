"""Immutable uploaded materials and pinned lecture settings."""
from alembic import op
import sqlalchemy as sa

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings_versions', sa.Column('material_ids', sa.JSON(), nullable=False, server_default='[]'))
    op.create_table('course_materials',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('lecture_id', sa.String(36), sa.ForeignKey('lectures.id'), nullable=True),
        sa.Column('name', sa.String(160), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('original', sa.Text(), nullable=False),
        sa.Column('pages', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_course_materials_course_id', 'course_materials', ['course_id'])
    op.create_index('ix_course_materials_lecture_id', 'course_materials', ['lecture_id'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
