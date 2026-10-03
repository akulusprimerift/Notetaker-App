"""Create a verified, point-in-time SQLite backup without copying live WAL files."""
import argparse
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


def backup_database(source_path, target_path):
    source = Path(source_path).expanduser().resolve(strict=True)
    target = Path(target_path).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('The backup destination already exists; choose a new path.')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f'.{target.name}.{uuid4().hex}.partial')
    source_db = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30)
    target_db = None
    try:
        target_db = sqlite3.connect(staging, timeout=30)
        source_db.backup(target_db)
        if target_db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('SQLite backup integrity check failed.')
        if target_db.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('SQLite backup foreign-key check failed.')
        target_db.commit()
        target_db.close()
        target_db = None
        os.chmod(staging, 0o600)
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
        return target
    except Exception:
        if target_db is not None:
            target_db.close()
        for suffix in ('', '-wal', '-shm'):
            try:
                Path(str(staging) + suffix).unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        source_db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Existing SQLite library file.')
    parser.add_argument('--target', type=Path, required=True, help='New backup file; it must not already exist.')
    args = parser.parse_args(argv)
    try:
        target = backup_database(args.source, args.target)
    except (FileExistsError, OSError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f'{exc}\n')
    print(target)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
