"""Read-only source backup; verify the note-section upgrade preserves every row."""
import argparse
import json
import os
import sqlite3
import subprocess
from pathlib import Path
from alembic import command
from alembic.config import Config
from notetaker.db import database


def rows(connection):
    result = {}
    tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'alembic_version'")
    for (name,) in tables.fetchall():
        quoted = '"'+name.replace('"', '""')+'"'
        columns = [r[1] for r in connection.execute('PRAGMA table_info('+quoted+')') if r[1] != 'source_ids']
        fields = ','.join('"'+c.replace('"', '""')+'"' for c in columns)
        result[name] = sorted(connection.execute('SELECT '+fields+' FROM '+quoted).fetchall(), key=repr)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--bundle', type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    destination = args.directory/'workspace.db'
    with sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro', uri=True) as source:
        with sqlite3.connect(destination) as target: source.backup(target)
    with sqlite3.connect(destination) as connection:
        before = rows(connection)
        old = connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        assert old == '0012', 'Use a pre-section library at migration 0012'
    url = 'sqlite:///'+destination.resolve().as_posix()
    def migrate():
        if args.bundle:
            env = {**os.environ, 'NOTETAKER_DATABASE_URL':url, 'NOTETAKER_STANDALONE':'true',
                   'NOTETAKER_PREVIEW':'false', 'NOTETAKER_AUDIO_DIRECTORY':str((args.directory/'audio').resolve())}
            subprocess.run([str(args.bundle.resolve()/'NotetakerService.exe'), 'migrate'],
                           env=env, check=True, timeout=90, capture_output=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        else:
            engine, _ = database(url)
            config = Config('alembic.ini')
            with engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
                assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar() == 1
            engine.dispose()
    migrate()
    with sqlite3.connect(destination) as connection:
        assert rows(connection) == before, 'Existing library rows changed'
        # Simulate a process exit after the SQLite table copy commits but before
        # Alembic writes its version. Only the isolated backup is modified.
        connection.execute("UPDATE alembic_version SET version_num='0012'")
    migrate()
    with sqlite3.connect(destination) as connection:
        assert rows(connection) == before, 'Existing library rows changed'
        assert connection.execute('SELECT count(*) FROM note_requests WHERE source_ids IS NOT NULL').fetchone()[0] == 0
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        version = connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    report = {'source_read_only':True, 'from':old, 'to':version, 'all_rows_preserved':True,
              'frozen_service':bool(args.bundle), 'interrupted_upgrade_resumed':True,
              'foreign_keys_enabled_after_upgrade':None if args.bundle else True, 'integrity':'ok',
              'table_counts':{name:len(items) for name,items in before.items()}}
    (args.directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
