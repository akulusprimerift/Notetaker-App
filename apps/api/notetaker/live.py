"""Durable, broker-independent UI replay. Events are invalidations, not model text."""
from sqlalchemy import select
from .models import LectureUpdate
from .security import authenticate, error
from .transcription import lock_lecture

REPLAY_LIMIT = 100


def replay(sessions, token, lecture_id, cursor, owned_lecture):
    with sessions() as db:
        session = authenticate(db, token)
        owned_lecture(db, session.owner_id, lecture_id)
        lecture = lock_lecture(db, lecture_id)
        if lecture.tombstoned: error(404, 'unavailable', 'This lecture is unavailable.')
        head = lecture.update_seq
        if cursor is None or cursor < 0 or cursor > head:
            return {'schema_version': 1, 'kind': 'snapshot_required', 'cursor': head}
        rows = db.scalars(select(LectureUpdate).where(LectureUpdate.lecture_id == lecture_id,
            LectureUpdate.sequence > cursor).order_by(LectureUpdate.sequence).limit(REPLAY_LIMIT)).all()
        if (rows and rows[0].sequence != cursor + 1) or (not rows and cursor != head) or any(
                b.sequence != a.sequence + 1 for a,b in zip(rows, rows[1:])):
            return {'schema_version': 1, 'kind': 'snapshot_required', 'cursor': head}
        return {'schema_version': 1, 'kind': 'updates' if rows else 'heartbeat',
            'cursor': rows[-1].sequence if rows else cursor,
            'events': [{'sequence': r.sequence, 'kind': r.kind, 'entity_id': r.entity_id,
                'entity_version': r.entity_version} for r in rows]}
