"""One inference slot per model role, coordinated by SQLite and OS file locks."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
from threading import Lock

from sqlalchemy import select, update
from sqlalchemy.engine import make_url

from .models import Owner, Job, now

_process_locks = {'speech': Lock(), 'notes': Lock()}


def available(db, kind='speech.window'):
    """Serialize claims with SQLite's writer lock, then check active leases."""
    db.execute(update(Owner).values(singleton=1))
    kinds = ('notes.generate', 'learning.generate') if kind == 'notes.generate' else (kind,)
    running = db.scalar(select(Job.id).where(Job.kind.in_(kinds),
        Job.status == 'running', Job.lease_expires_at > now()).limit(1))
    return not running


def _lock_file(file):
    """Try an exclusive process lock; the lock is released by the OS on exit."""
    if os.name == 'nt':
        import msvcrt
        file.seek(0, os.SEEK_END)
        if file.tell() == 0:
            file.write(b'0')
            file.flush()
        file.seek(0)
        try:
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            busy_errors = {errno.EACCES, errno.EAGAIN}
            busy_errors.update(value for name in ('EDEADLK', 'EDEADLOCK')
                if (value := getattr(errno, name, None)) is not None)
            if exc.errno in busy_errors:
                return False, None
            raise
        return True, 'windows'

    import fcntl
    try:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False, None
    return True, 'posix'


def _unlock_file(file, kind):
    if kind == 'windows':
        import msvcrt
        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
    elif kind == 'posix':
        import fcntl
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


@contextmanager
def inference_slot(sessions, kind='speech.window'):
    """Hold one per-role slot across inference without holding a DB transaction.

    SQLite serializes claims through a no-op owner update and fenced job leases.
    This OS lock also prevents an expired lease from starting overlapping model
    work in another process. All workers for one library must share its local
    filesystem; network filesystems are not supported.
    """
    slot = 'notes' if kind in ('notes.generate', 'learning.generate') else 'speech'
    local = _process_locks[slot]
    local_acquired = local.acquire(blocking=False)
    if not local_acquired:
        yield False
        return
    acquired = True
    file = None
    file_lock = None
    try:
        bind = getattr(sessions, 'kw', {}).get('bind')
        url = make_url(bind.url) if bind is not None else None
        database_path = url.database if url and url.get_backend_name() == 'sqlite' else None
        if database_path and database_path != ':memory:':
            lock_path = Path(database_path).expanduser().resolve()
            lock_path = lock_path.with_name(lock_path.name + f'.{slot}.lock')
            file = lock_path.open('a+b')
            try:
                os.chmod(lock_path, 0o600)
            except OSError:
                pass
            acquired, file_lock = _lock_file(file)
            if not acquired:
                file.close()
                file = None
        yield acquired
    finally:
        if file is not None:
            try:
                _unlock_file(file, file_lock)
            finally:
                file.close()
        local.release()
