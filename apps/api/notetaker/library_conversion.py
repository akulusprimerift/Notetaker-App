"""Explicit, verified conversion into a new SQLite library; never edits the source."""
from datetime import datetime
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text

from .db import database
from .local_audio_store import LocalAudioStore
from .models import Base
from .runtime_platform import protect_library


def digest_rows(rows):
    def encode(value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError('Unsupported library value')
    return hashlib.sha256(json.dumps(rows, default=encode, sort_keys=True,
        ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def convert_library(source_engine, source_store, destination):
    """The caller must pause the source app/workers before conversion.

    One source snapshot pins all histories. Publication requires equal rows,
    valid foreign keys, SQLite integrity and checksum-matching retained audio.
    A failed conversion leaves an inspectable staging folder, never a usable
    destination. Existing destination folders are always refused.
    """
    destination = Path(destination).absolute()
    if destination.exists():
        raise RuntimeError('Choose a new destination folder. Existing libraries are never replaced.')
    staging = destination.with_name(destination.name + '.pending-' + uuid4().hex)
    staging.mkdir(parents=True)
    protect_library(staging)
    marker = staging / 'conversion.pending'
    marker.write_text('Conversion has not completed. Keep the original library.', encoding='utf-8')
    engine, _ = database('sqlite:///' + (staging / 'workspace.sqlite3').as_posix())
    store = LocalAudioStore(staging / 'audio')
    counts, hashes, records, objects = {}, {}, {}, {}
    try:
        config = Config()
        config.set_main_option('script_location', str(Path(__file__).parents[1] / 'migrations'))
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
        with source_engine.connect() as source:
            if source_engine.dialect.name == 'postgresql':
                source = source.execution_options(isolation_level='REPEATABLE READ')
                source.execute(text('SET TRANSACTION READ ONLY'))
            else:
                # Synthetic/local source snapshot; also excludes source writes during copy.
                source.exec_driver_sql('BEGIN IMMEDIATE')
            with engine.connect() as target:
                revision = target.scalar(text('SELECT version_num FROM alembic_version'))
            if source.scalar(text('SELECT version_num FROM alembic_version')) != revision:
                raise RuntimeError('Update the earlier app to schema ' + revision + ' before converting.')
            schema = inspect(source)
            tables = sorted(Base.metadata.tables.values(), key=lambda table: table.name)
            if set(schema.get_table_names()) != {table.name for table in tables} | {'alembic_version'}:
                raise RuntimeError('The source schema differs. Conversion retained all original files.')
            for table in tables:
                if {column['name'] for column in schema.get_columns(table.name)} != set(table.c.keys()):
                    raise RuntimeError('The source schema differs for ' + table.name)
                rows = [dict(row) for row in source.execute(select(table).order_by(*table.primary_key.columns)).mappings()]
                records[table.name] = rows
                counts[table.name], hashes[table.name] = len(rows), digest_rows(rows)
            with engine.begin() as target:
                target.exec_driver_sql('PRAGMA defer_foreign_keys=ON')
                for table in tables:
                    rows = records[table.name]
                    for offset in range(0, len(rows), 250):
                        target.execute(table.insert(), rows[offset:offset + 250])
            source_store.ready()
            for key in source_store.list_keys(''):
                data = source_store.read(key)
                if len(data) > 8 * 1024 * 1024:
                    raise RuntimeError('An audio object exceeds the supported limit. Conversion was not published.')
                checksum = hashlib.sha256(data).hexdigest()
                store.write_verified(key, data, checksum)
                objects[key] = {'bytes': len(data), 'sha256': checksum}
            lectures = {row['id']: row for row in records['lectures']}
            runs = {row['id']: row for row in records['capture_runs']}
            verified = {row['id'] for row in records['audio_chunks']}
            for row in records['upload_reservations']:
                if row['id'] not in verified:
                    continue
                identity, lecture, run = row['identity'], lectures[row['lecture_id']], runs[row['run_id']]
                released = identity['start_sample'] + identity['sample_count'] <= run['released_through']
                expected = {'bytes': identity['byte_length'], 'sha256': identity['sha256']}
                actual = objects.get(row['object_key'])
                if actual is not None and actual != expected:
                    raise RuntimeError('An original audio checksum differs. Conversion was not published.')
                if actual is None and not (released or lecture['audio_removed'] or lecture['tombstoned']):
                    raise RuntimeError('Retained audio is missing. Conversion was not published.')
        with engine.connect() as target:
            for table in tables:
                rows = [dict(row) for row in target.execute(select(table).order_by(*table.primary_key.columns)).mappings()]
                if digest_rows(rows) != hashes[table.name]:
                    raise RuntimeError('Converted records differ for ' + table.name)
            if target.exec_driver_sql('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('Converted SQLite integrity check failed.')
            if target.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
                raise RuntimeError('Converted SQLite foreign key check failed.')
        report = {'schema_version': 1, 'database': 'sqlite', 'source_database': source_engine.dialect.name,
            'table_counts': counts, 'table_sha256': hashes, 'audio_files': objects,
            'source_modified': False, 'credentials_copied': False}
        engine.dispose()
        # Checkpoint before publishing; the three SQLite files must never be copied separately.
        import sqlite3
        with closing(sqlite3.connect(staging / 'workspace.sqlite3')) as connection:
            connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        with (staging / 'conversion-report.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        if destination.exists():
            raise RuntimeError('The destination appeared during conversion; existing files were retained.')
        marker.unlink()
        staging.rename(destination)
        return report
    finally:
        engine.dispose()
