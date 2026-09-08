"""One inference slot per model workload, independent of capture.

Claims share the owner lock. PostgreSQL additionally holds a session advisory lock
through provider execution: an expired lease cannot overlap the same workload.
Speech and notes may run concurrently. SQLite uses in-process locks for preview.
"""
from contextlib import contextmanager
from threading import Lock
from sqlalchemy import select, update, text
from .models import Owner, Job, now

_preview_locks = {'speech.window': Lock(), 'notes.generate': Lock()}
BUDGET_KEY = 684005


def available(db, kind='speech.window'):
    # Always acquire before the lecture lock (same ordering as command receipts).
    if db.bind.dialect.name == 'sqlite':
        db.execute(update(Owner).values(singleton=1))
    else:
        db.scalar(select(Owner).with_for_update())
    running = db.scalar(select(Job.id).where(Job.kind == kind,
        Job.status == 'running', Job.lease_expires_at > now()).limit(1))
    return not running


@contextmanager
def inference_slot(sessions, kind='speech.window'):
    with sessions() as db:
        if db.bind.dialect.name == 'postgresql':
            # Keep this dedicated connection pinned until inference has stopped.
            connection = db.connection()
            key = BUDGET_KEY + (1 if kind == 'notes.generate' else 0)
            acquired = connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': key})
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': key})
        else:
            lock = _preview_locks[kind]
            acquired = lock.acquire(blocking=False)
            try:
                yield acquired
            finally:
                if acquired: lock.release()
