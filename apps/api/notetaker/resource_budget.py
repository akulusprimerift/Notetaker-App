"""One cross-process inference slot per workload, independent of capture.

SQLite writer transactions serialize claims. OS file locks hold each inference
slot until the provider stops, even if its database lease expires. Speech and
notes can run together; learning questions share the notes slot.
"""
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from sqlalchemy import select, update
from .models import Owner, Job, now
from .sqlite_lock import exclusive_file_lock

_memory_locks = {'speech.window': Lock(), 'notes.generate': Lock()}


def available(db, kind='speech.window'):
    db.execute(update(Owner).values(singleton=1))
    kinds = ('notes.generate', 'learning.generate') if kind == 'notes.generate' else (kind,)
    running = db.scalar(select(Job.id).where(Job.kind.in_(kinds),
        Job.status == 'running', Job.lease_expires_at > now()).limit(1))
    return not running


@contextmanager
def inference_slot(sessions, kind='speech.window'):
    if kind not in _memory_locks:
        raise ValueError('Unknown inference workload')
    with sessions() as db:
        filename = db.bind.url.database
    if filename and filename != ':memory:':
        lock_path = Path(filename).resolve().with_name(Path(filename).name + '.' + kind + '.lock')
        with exclusive_file_lock(lock_path) as acquired:
            yield acquired
    else:
        lock = _memory_locks[kind]
        acquired = lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()
