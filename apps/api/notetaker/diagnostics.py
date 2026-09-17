"""Read-only, content-free processing diagnostics from authoritative job state."""
from sqlalchemy import case, func, or_, select

from .models import Course, Job, Lecture, now


def processing_snapshot(db, owner_id, *, sampled_at=None):
    sampled_at = sampled_at or now()
    ready = (Job.status == 'due') & (Job.due_at <= sampled_at)
    delayed = (Job.status == 'due') & (Job.due_at > sampled_at)
    expired = (Job.status == 'running') & or_(
        Job.lease_expires_at.is_(None), Job.lease_expires_at <= sampled_at)
    statement = select(
        Job.kind, Job.status, func.count(Job.id),
        func.sum(case((ready, 1), else_=0)),
        func.sum(case((delayed, 1), else_=0)),
        func.sum(case((expired, 1), else_=0)),
        func.min(case((ready, Job.due_at), else_=None)),
    ).join(Lecture, Job.lecture_id == Lecture.id).join(Course, Lecture.course_id == Course.id).where(
        Course.owner_id == owner_id, Course.tombstoned.is_(False), Lecture.tombstoned.is_(False),
        Job.lifecycle_epoch == Lecture.lifecycle_epoch,
        or_(Job.audio_epoch.is_(None), Job.audio_epoch == Lecture.audio_epoch),
        Job.status.in_(['due', 'running', 'failed']),
    ).group_by(Job.kind, Job.status).order_by(Job.kind, Job.status)
    groups = []
    for kind, status, count, ready_count, delayed_count, expired_count, oldest_due in db.execute(statement):
        groups.append({'kind': kind, 'status': status, 'count': count,
            'ready_count': ready_count, 'delayed_count': delayed_count,
            'expired_lease_count': expired_count,
            'oldest_due_seconds': max(0, (sampled_at - oldest_due).total_seconds()) if oldest_due else None})
    return {'sampled_at': sampled_at.isoformat() + 'Z', 'groups': groups,
        'scope': 'current_epoch_jobs_in_visible_lectures',
        'timing_basis': 'current_due_time_not_end_to_end_latency'}
