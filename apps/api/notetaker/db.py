import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def database(url: str):
    parsed = make_url(url)
    if parsed.get_backend_name() != 'sqlite':
        raise ValueError('The application database must be SQLite.')
    database_path = parsed.database
    if database_path and database_path != ':memory:':
        Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    engine = create_engine(url, pool_pre_ping=True, connect_args={
        "check_same_thread": False,
        "timeout": 30,
    })
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            if database_path and database_path != ':memory:':
                try:
                    os.chmod(Path(database_path).expanduser().resolve(), 0o600)
                except OSError:
                    pass
    return engine, sessionmaker(engine, expire_on_commit=False)
