"""Pin bounded note sections without replacing existing source or note history."""
from alembic import op
import sqlalchemy as sa

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def alter():
    convention = {'uq': 'uq_%(table_name)s_%(column_0_name)s'}
    with op.batch_alter_table('note_requests', naming_convention=convention) as batch:
        batch.add_column(sa.Column('source_ids', sa.JSON(), nullable=True))
        batch.drop_constraint('uq_note_requests_snapshot_id', type_='unique')
        batch.create_unique_constraint('uq_note_request_batch',
            ['snapshot_id', 'preference_id', 'settings_id', 'base_revision'])


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'sqlite':
        # A process exit after the atomic table copy but before Alembic stamps
        # its version must be restartable without copying or changing history.
        inspector = sa.inspect(connection)
        if (any(c['name'] == 'source_ids' for c in inspector.get_columns('note_requests')) and
                any(c['column_names'] == ['snapshot_id', 'preference_id', 'settings_id', 'base_revision']
                    for c in inspector.get_unique_constraints('note_requests'))):
            return
        # SQLite must copy the table to change a unique constraint. Disable FK
        # enforcement outside a transaction; verify every retained reference.
        # The desktop and tests may supply an externally managed connection,
        # for which Alembic's autocommit_block is unavailable. Finish prior
        # migrations, then perform this table copy in its own atomic savepoint.
        driver = connection.connection.driver_connection
        driver.commit()
        driver.execute('PRAGMA foreign_keys=OFF')
        try:
            with connection.begin_nested():
                alter()
                if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
                    raise RuntimeError('Note batch migration found invalid references')
        finally:
            driver.execute('PRAGMA foreign_keys=ON')
    else:
        # PostgreSQL names the original unnamed unique constraint itself.
        constraints = sa.inspect(connection).get_unique_constraints('note_requests')
        original = next(c['name'] for c in constraints if c['column_names'] ==
            ['snapshot_id', 'preference_id', 'settings_id'])
        op.add_column('note_requests', sa.Column('source_ids', sa.JSON(), nullable=True))
        op.drop_constraint(original, 'note_requests', type_='unique')
        op.create_unique_constraint('uq_note_request_batch', 'note_requests',
            ['snapshot_id', 'preference_id', 'settings_id', 'base_revision'])


def downgrade():
    raise RuntimeError('Destructive downgrade refused. Restore a verified backup instead.')
