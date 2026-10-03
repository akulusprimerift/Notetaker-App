"""Copy an existing PostgreSQL library into a new, current SQLite database.

The source is opened read-only in one repeatable-read snapshot. The destination
must not exist; schema upgrades and data transfer happen in an adjacent staging
file, which is atomically published only after integrity and row checks pass.
"""
import argparse
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

from .db import database

ROOT = Path(__file__).resolve().parents[3]
CHUNK_SIZE = 500


def _script_directory():
    return ScriptDirectory.from_config(Config(str(ROOT / 'alembic.ini')))


def _head_revision(script):
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError('The application migration graph must have exactly one head.')
    return heads[0]


def _revision(connection):
    if not inspect(connection).has_table('alembic_version'):
        raise RuntimeError('The source has no Alembic version table.')
    rows = connection.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    if len(rows) != 1:
        raise RuntimeError('The source must have exactly one Alembic revision.')
    return rows[0]


def _validate_source_revision(script, source_revision):
    if script.get_revision(source_revision) is None:
        raise RuntimeError('The source schema revision is not present in this application.')
    try:
        list(script.iterate_revisions('head', source_revision))
    except Exception as exc:
        raise RuntimeError('The source schema revision is not an ancestor of the current application schema.') from exc


def _upgrade(connection, revision):
    config = Config(str(ROOT / 'alembic.ini'))
    config.attributes['connection'] = connection
    command.upgrade(config, revision)


def _json_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {'bytes_hex': value.hex()}
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f'Unsupported database value type: {type(value).__name__}')


def _row_digest(connection, table, column_names):
    primary_key = list(table.primary_key.columns)
    if not primary_key:
        raise RuntimeError(f'The source table {table.name} has no primary key for stable verification.')
    columns = [table.c[name] for name in column_names]
    statement = select(*columns).order_by(*primary_key)
    result = connection.execution_options(stream_results=True).execute(statement)
    digest = hashlib.sha256()
    count = 0
    while True:
        rows = result.fetchmany(CHUNK_SIZE)
        if not rows:
            break
        for row in rows:
            encoded = json.dumps(_json_value(dict(row._mapping)), sort_keys=True,
                ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            digest.update(len(encoded).to_bytes(8, 'big'))
            digest.update(encoded)
            count += 1
    return count, digest.hexdigest()


def _copy_at_source_revision(source, target):
    source_meta = MetaData()
    source_meta.reflect(bind=source)
    target_meta = MetaData()
    target_meta.reflect(bind=target)
    source_tables = {table.name: table for table in source_meta.sorted_tables if table.name != 'alembic_version'}
    target_tables = {table.name: table for table in target_meta.sorted_tables if table.name != 'alembic_version'}
    if source_tables.keys() != target_tables.keys():
        missing = sorted(source_tables.keys() - target_tables.keys())
        extra = sorted(target_tables.keys() - source_tables.keys())
        raise RuntimeError(f'Source and target tables differ at the source revision (missing={missing}, extra={extra}).')

    for name, source_table in source_tables.items():
        target_table = target_tables[name]
        source_columns = [column.name for column in source_table.columns]
        target_columns = [column.name for column in target_table.columns]
        if source_columns != target_columns:
            raise RuntimeError(f'Source and target columns differ for {name}; no data was published.')
        rows = source.execution_options(stream_results=True).execute(select(source_table))
        while batch := rows.mappings().fetchmany(CHUNK_SIZE):
            target.execute(target_table.insert(), [dict(row) for row in batch])

    source_digest = {}
    for name, table in source_tables.items():
        source_digest[name] = _row_digest(source, table, [column.name for column in table.columns])
    for name, table in target_tables.items():
        target_digest = _row_digest(target, table, [column.name for column in table.columns])
        if target_digest != source_digest[name]:
            raise RuntimeError(f'Imported data verification failed for {name}.')
    return source_digest


def _check_sqlite(connection):
    integrity = connection.exec_driver_sql('PRAGMA integrity_check').scalar_one()
    if integrity != 'ok':
        raise RuntimeError(f'SQLite integrity check failed: {integrity}')
    foreign_key_errors = connection.exec_driver_sql('PRAGMA foreign_key_check').all()
    if foreign_key_errors:
        raise RuntimeError(f'SQLite foreign-key verification failed with {len(foreign_key_errors)} row(s).')


def _publish_staging(engine, staging, target):
    with engine.connect() as connection:
        _check_sqlite(connection)
        connection.exec_driver_sql('PRAGMA wal_checkpoint(TRUNCATE)')
        connection.commit()
    engine.dispose()
    # A hard-link publish is atomic and fails if another process created target
    # after the initial absence check; os.replace would silently overwrite it.
    os.link(staging, target)
    staging.unlink()
    try:
        descriptor = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        # Directory fsync is not available on every supported Windows filesystem.
        pass


def migrate_database(source_engine, target_path):
    """Stage and verify a migration from PostgreSQL or a synthetic SQLite source."""
    target = Path(target_path).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('The SQLite destination already exists; choose a new path and retain the existing file.')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f'.{target.name}.{uuid4().hex}.partial')
    target_url = URL.create('sqlite', database=str(staging))
    target_engine, _ = database(target_url.render_as_string(hide_password=False))
    script = _script_directory()
    try:
        with source_engine.connect() as source:
            if source.dialect.name == 'postgresql':
                source = source.execution_options(isolation_level='REPEATABLE READ')
                source.execute(text('SET TRANSACTION READ ONLY'))
            elif source.dialect.name == 'sqlite':
                source.exec_driver_sql('BEGIN')
            else:
                raise RuntimeError('The conversion source must be PostgreSQL (SQLite is accepted for synthetic converter tests).')
            source_revision = _revision(source)
            _validate_source_revision(script, source_revision)
            with target_engine.begin() as target_connection:
                _upgrade(target_connection, source_revision)
            with target_engine.begin() as target_connection:
                target_connection.exec_driver_sql('PRAGMA defer_foreign_keys=ON')
                copied = _copy_at_source_revision(source, target_connection)
            with target_engine.begin() as target_connection:
                _upgrade(target_connection, 'head')
            head = _head_revision(script)
            with target_engine.connect() as target_connection:
                final_revision = _revision(target_connection)
                if final_revision != head:
                    raise RuntimeError('The SQLite destination did not reach the current migration head.')
                _check_sqlite(target_connection)
            _publish_staging(target_engine, staging, target)
        overall = hashlib.sha256(''.join(f'{name}:{count}:{digest}\n'
            for name, (count, digest) in sorted(copied.items())).encode()).hexdigest()
        return {
            'source_revision': source_revision,
            'destination_revision': head,
            'tables': {name: count for name, (count, _) in sorted(copied.items())},
            'source_rows_sha256': overall,
            'destination': str(target),
        }
    except Exception:
        target_engine.dispose()
        for suffix in ('', '-wal', '-shm'):
            try:
                Path(str(staging) + suffix).unlink()
            except FileNotFoundError:
                pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True, help='New SQLite destination; it must not already exist.')
    args = parser.parse_args(argv)
    source_url = os.environ.get('NOTETAKER_POSTGRES_EXPORT_URL', '')
    if not source_url:
        parser.error('Set NOTETAKER_POSTGRES_EXPORT_URL to the existing PostgreSQL connection URL.')
    try:
        parsed = make_url(source_url)
    except Exception:
        parser.error('NOTETAKER_POSTGRES_EXPORT_URL is not a valid SQLAlchemy URL.')
    if parsed.drivername != 'postgresql+psycopg':
        parser.error('NOTETAKER_POSTGRES_EXPORT_URL must use postgresql+psycopg.')
    try:
        from sqlalchemy import create_engine
        source_engine = create_engine(parsed, pool_pre_ping=True, connect_args={'connect_timeout': 5})
        try:
            result = migrate_database(source_engine, args.target)
        finally:
            source_engine.dispose()
        print(json.dumps(result, sort_keys=True, indent=2))
    except (FileExistsError, RuntimeError, SQLAlchemyError, OSError, TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
