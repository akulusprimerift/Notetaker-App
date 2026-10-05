from alembic import context
from notetaker.config import Settings
from notetaker.db import database
from notetaker.models import Base

config=context.config


def run(connection):
    if not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN IMMEDIATE')
    context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=Settings().database_url,target_metadata=Base.metadata,literal_binds=True,dialect_opts={"paramstyle":"named"})
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run(config.attributes["connection"])
else:
    engine,_=database(Settings().database_url)
    # The explicit SQLite BEGIN makes Alembic treat this as an external
    # transaction. Own its commit here, just like caller-supplied migrations.
    with engine.begin() as connection:
        run(connection)
    engine.dispose()
