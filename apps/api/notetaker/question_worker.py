"""Low-priority, leased question generation in the existing note worker process."""
import logging
import threading
import time
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, or_
from . import models as m
from .notes import latest
from .note_provider import NoteFailure
from .question_contract import validate_questions
from .questions import source_current
from .resource_budget import available, inference_slot
from .transcription import lock_lecture

LEASE_SECONDS = 60
log = logging.getLogger('notetaker.questions')


def current_input(db, job, lecture):
    row = db.get(m.QuestionSet, job.input_revision)
    if not row or not lecture or lecture.tombstoned or row.content is not None:
        return False
    pref = latest(db, m.NotePreference, lecture.id, m.NotePreference.version)
    settings = latest(db, m.SettingsVersion, lecture.id, m.SettingsVersion.version)
    return (job.lifecycle_epoch == lecture.lifecycle_epoch and job.audio_epoch == lecture.audio_epoch
        and pref is not None and pref.enabled and row.preference_id == pref.id
        and settings is not None and row.settings_id == settings.id and source_current(db, lecture, row))


def claim(sessions):
    with sessions() as db:
        if not available(db, 'notes.generate'):
            return None
        jobs = db.scalars(select(m.Job).where(m.Job.kind == 'learning.generate',
            or_((m.Job.status == 'due') & (m.Job.due_at <= m.now()),
                (m.Job.status == 'running') & (m.Job.lease_expires_at <= m.now())))
            .order_by(m.Job.due_at, m.Job.id)).all()
        for job in jobs:
            lecture = lock_lecture(db, job.lecture_id)
            if not current_input(db, job, lecture):
                job.status = 'cancelled'; continue
            job.status = 'running'; job.attempt_token = str(uuid4()); job.attempts += 1
            job.lease_expires_at = m.now() + timedelta(seconds=LEASE_SECONDS); job.error_code = None
            db.get(m.QuestionSet, job.input_revision).preview = ''
            db.commit()
            return job.id, job.attempt_token
        db.commit()
    return None


def live(db, job_id, token):
    job = db.get(m.Job, job_id)
    if not job:
        return None
    lecture = lock_lecture(db, job.lecture_id)
    db.refresh(job)
    if job.status != 'running' or job.attempt_token != token or not job.lease_expires_at or job.lease_expires_at <= m.now():
        return None
    if not current_input(db, job, lecture):
        job.status = 'cancelled'; db.commit(); return None
    return job, db.get(m.QuestionSet, job.input_revision)


def renew(sessions, job_id, token):
    with sessions() as db:
        active = live(db, job_id, token)
        if not active:
            return False
        active[0].lease_expires_at = m.now() + timedelta(seconds=LEASE_SECONDS)
        db.commit()
        return True


def publish(sessions, job_id, token, output, metadata):
    with sessions() as db:
        active = live(db, job_id, token)
        if not active:
            return False
        job, row = active
        # Enforce validation again at the persistence boundary, even for injected adapters.
        canonical = validate_questions({'questions': [{k: v for k, v in q.items() if k != 'id'} for q in output]}, row.evidence)
        pref = db.get(m.NotePreference, row.preference_id)
        if metadata.get('model') != pref.model or metadata.get('model_digest') != pref.model_digest:
            raise ValueError('model_identity')
        row.content = canonical; row.metadata_json = metadata; row.preview = ''
        job.status = 'completed'; job.lease_expires_at = None; job.error_code = None
        db.commit()
        return True


def fail(sessions, job_id, token, code):
    with sessions() as db:
        active = live(db, job_id, token)
        if not active:
            return
        job, row = active
        retry = code == 'resource_busy' or (code in ('model_unavailable', 'worker_error') and job.attempts < 3)
        job.status = 'due' if retry else 'failed'; job.error_code = code
        job.due_at = m.now() + timedelta(seconds=60); job.lease_expires_at = None; row.preview = ''
        db.commit()


def execute(sessions, provider, chosen, heartbeat=True):
    stop = threading.Event()
    def beat():
        while not stop.wait(10):
            try:
                if not renew(sessions, *chosen): return
            except Exception: return
    thread = threading.Thread(target=beat, daemon=True)
    if heartbeat: thread.start()
    try:
        with sessions() as db:
            active = live(db, *chosen)
            if not active: return False
            row = active[1]; evidence = row.evidence
            pref = db.get(m.NotePreference, row.preference_id); db.expunge(pref)
        last = [0.0]
        def preview(value):
            if time.monotonic() - last[0] < .3: return
            with sessions() as db:
                active = live(db, *chosen)
                if not active: raise NoteFailure('superseded')
                active[1].preview = value[-24000:]; db.commit()
            last[0] = time.monotonic()
        with inference_slot(sessions, 'notes.generate') as acquired:
            if not acquired: raise NoteFailure('resource_busy')
            output, metadata = provider.generate_questions(evidence, pref, preview)
        return publish(sessions, *chosen, output, metadata)
    except NoteFailure as exc:
        fail(sessions, *chosen, exc.code)
    except (ValueError, KeyError, TypeError):
        fail(sessions, *chosen, 'invalid_output')
    except Exception:
        log.warning('Question generation failed: job=%s', chosen[0])
        fail(sessions, *chosen, 'worker_error')
    finally:
        stop.set()
        if heartbeat: thread.join(timeout=2)
    return False
