"""One inference slot shared by speech and notes, independent of capture.

Claims share the owner lock. PostgreSQL additionally holds a session advisory lock
through provider execution: an expired job lease cannot start overlapping inference.
SQLite is a development/test preview and uses an in-process execution lock.
"""
from contextlib import contextmanager
from threading import Lock
from sqlalchemy import select, update, text
from .models import Owner, Job, now

_preview_lock = Lock()
BUDGET_KEY = 684005


def available(db):
    # Always acquire before the lecture lock (same ordering as command receipts).
    if db.bind.dialect.name == 'sqlite':
        db.execute(update(Owner).values(singleton=1))
    else:
        db.scalar(select(Owner).with_for_update())
    running = db.scalar(select(Job.id).where(Job.kind.in_(['speech.window', 'notes.generate']),
        Job.status == 'running', Job.lease_expires_at > now()).limit(1))
    return not running


@contextmanager
def inference_slot(sessions):
    with sessions() as db:
        if db.bind.dialect.name == 'postgresql':
            # Keep this dedicated connection pinned until inference has stopped.
            connection = db.connection()
            acquired = connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': BUDGET_KEY})
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': BUDGET_KEY})
        else:
            acquired = _preview_lock.acquire(blocking=False)
            try:
                yield acquired
            finally:
                if acquired: _preview_lock.release()
