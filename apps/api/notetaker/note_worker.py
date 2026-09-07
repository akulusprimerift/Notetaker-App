"""One local note request at a time, recovered from PostgreSQL after worker exits."""
import logging
import threading
import time
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, or_, update
from jsonschema import ValidationError
from .config import Settings
from .db import database
from .models import (Owner, Lecture, Job, NoteRequest, NotePreference, NoteRevision,
    TranscriptSnapshot, SettingsVersion, LectureUpdate, now)
from .transcription import lock_lecture, transcript_json
from .notes import latest, schedule_notes, inputs
from .note_provider import OllamaNotes, NoteFailure
from .note_contract import validate_notes

LEASE_SECONDS = 60
log = logging.getLogger('notetaker.notes')


def current_input(db, job, lecture):
    request = db.get(NoteRequest, job.input_revision)
    if not request or not lecture or lecture.tombstoned: return False
    pref = latest(db, NotePreference, lecture.id, NotePreference.version)
    snapshot = latest(db, TranscriptSnapshot, lecture.id, TranscriptSnapshot.sequence)
    settings = latest(db, SettingsVersion, lecture.id, SettingsVersion.version)
    revision = latest(db, NoteRevision, lecture.id, NoteRevision.revision)
    return (job.lifecycle_epoch == lecture.lifecycle_epoch and job.audio_epoch == lecture.audio_epoch
        and pref is not None and pref.enabled and request.preference_id == pref.id
        and snapshot is not None and request.snapshot_id == snapshot.id and request.settings_id == settings.id
        and request.base_revision == (revision.revision if revision else 0))


def plan(sessions):
    with sessions() as db:
        ids = db.scalars(select(NotePreference.lecture_id).distinct()).all()
    for lecture_id in ids:
        with sessions() as db:
            lecture = lock_lecture(db, lecture_id)
            if lecture: schedule_notes(db, lecture)
            db.commit()


def claim(sessions):
    with sessions() as db:
        # Single-owner lock serializes all note claims even with duplicate worker processes.
        if db.bind.dialect.name == 'sqlite': db.execute(update(Owner).values(singleton=1))
        else: db.scalar(select(Owner).with_for_update())
        running = db.scalar(select(Job.id).where(Job.kind == 'notes.generate', Job.status == 'running', Job.lease_expires_at > now()).limit(1))
        if running: return None
        jobs = db.scalars(select(Job).where(Job.kind == 'notes.generate',
            or_((Job.status == 'due') & (Job.due_at <= now()), (Job.status == 'running') & (Job.lease_expires_at <= now())))
            .order_by(Job.due_at, Job.id)).all()
        for job in jobs:
            lecture = lock_lecture(db, job.lecture_id)
            if not current_input(db, job, lecture): job.status = 'cancelled'; continue
            # Capture and speech have priority; no additional local note load until saved speech is done.
            if lecture.status == 'recording' or transcript_json(db, lecture)['status'] != 'processed': continue
            job.status = 'running'; job.attempt_token = str(uuid4()); job.attempts += 1
            job.lease_expires_at = now() + timedelta(seconds=LEASE_SECONDS); job.error_code = None
            db.commit(); return job.id, job.attempt_token
        db.commit()
    return None


def live(db, job_id, token):
    job = db.get(Job, job_id)
    if not job: return None
    lecture = lock_lecture(db, job.lecture_id)
    db.refresh(job)
    if job.status != 'running' or job.attempt_token != token or not job.lease_expires_at or job.lease_expires_at <= now(): return None
    if not current_input(db, job, lecture):
        job.status = 'cancelled'; db.commit(); return None
    return job, lecture


def renew(sessions, job_id, token):
    with sessions() as db:
        active = live(db, job_id, token)
        if not active: return False
        active[0].lease_expires_at = now() + timedelta(seconds=LEASE_SECONDS)
        db.commit(); return True


def publish(sessions, job_id, token, output, metadata):
    with sessions() as db:
        active = live(db, job_id, token)
        if not active: return False
        job, lecture = active
        request = db.get(NoteRequest, job.input_revision)
        evidence = inputs(db, request)
        resolved = validate_notes(output, evidence)
        pref = db.get(NotePreference, request.preference_id)
        if metadata.get('model_digest') != pref.model_digest or metadata.get('model') != pref.model: raise ValueError('model_identity')
        revision = NoteRevision(lecture_id=lecture.id, request_id=request.id, revision=request.base_revision + 1,
            attempt_token=token, content=output, resolved_citations=resolved, metadata_json=metadata)
        db.add(revision); db.flush()
        job.status = 'completed'; job.lease_expires_at = None; job.error_code = None
        lecture.update_seq += 1
        db.add(LectureUpdate(lecture_id=lecture.id, sequence=lecture.update_seq, kind='notes.changed', entity_id=revision.id, entity_version=revision.revision))
        db.commit(); return True


def fail(sessions, job_id, token, code):
    with sessions() as db:
        active = live(db, job_id, token)
        if not active: return
        job, _ = active
        transient = code in ('model_unavailable', 'worker_error') and job.attempts < 3
        job.status = 'due' if transient else 'failed'
        job.due_at = now() + timedelta(seconds=60)
        job.error_code = code; job.lease_expires_at = None
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
            request = db.get(NoteRequest, active[0].input_revision)
            evidence = inputs(db, request)
            pref = db.get(NotePreference, request.preference_id); db.expunge(pref)
        output, metadata = provider.generate(evidence, pref)
        return publish(sessions, *chosen, output, metadata)
    except NoteFailure as exc: fail(sessions, *chosen, exc.code)
    except (ValueError, KeyError, TypeError, ValidationError): fail(sessions, *chosen, 'invalid_output')
    except Exception:
        log.warning('Note attempt failed: job=%s', chosen[0])
        fail(sessions, *chosen, 'worker_error')
    finally:
        stop.set()
        if heartbeat: thread.join(timeout=2)
    return False


def main():
    settings = Settings()
    engine, sessions = database(settings.database_url)
    provider = OllamaNotes(settings)
    try:
        while True:
            try:
                plan(sessions)
                chosen = claim(sessions)
                if chosen: execute(sessions, provider, chosen)
                else: time.sleep(3)
            except Exception:
                log.warning('Note worker is waiting for its local database')
                time.sleep(5)
    finally: engine.dispose()


if __name__ == '__main__': main()
