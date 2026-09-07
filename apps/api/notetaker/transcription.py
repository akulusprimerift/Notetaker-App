"""Saved-audio transcription: immutable sources and explicit human corrections."""
import io
import wave
from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update, func
from .models import (Lecture, CaptureRun, AudioManifestRevision, UploadReservation, Job,
    SpeechWindow, TranscriptSegment, TranscriptVersion, TranscriptSnapshot,
    TranscriptSnapshotItem, CommandReceipt, LectureUpdate, Outbox, NoteRevision, now)
from .security import error, mutation

CORE_SECONDS = 24
CONTEXT_SECONDS = 2


def lock_lecture(db, lecture_id):
    if db.bind.dialect.name == 'sqlite':
        db.execute(update(Lecture).where(Lecture.id == lecture_id).values(update_seq=Lecture.update_seq))
    return db.scalar(select(Lecture).where(Lecture.id == lecture_id).with_for_update().execution_options(populate_existing=True))


def current_runs(db, lecture):
    return db.scalars(select(CaptureRun).where(CaptureRun.lecture_id == lecture.id,
        CaptureRun.lifecycle_epoch == lecture.lifecycle_epoch, CaptureRun.audio_epoch == lecture.audio_epoch)
        .order_by(CaptureRun.capture_epoch)).all()


def schedule(db, lecture, planned_cuts=None):
    """Called under the lecture lock. Only complete sealed snapshots are inference inputs."""
    made = 0
    for run in current_runs(db, lecture):
        revision = db.scalar(select(AudioManifestRevision).where(
            AudioManifestRevision.run_id == run.id, AudioManifestRevision.version == run.manifest_version))
        if not revision or not revision.content['complete']:
            continue
        if planned_cuts is not None and (run.id,run.manifest_version) not in planned_cuts:
            continue
        boundaries = sorted({0, run.final_sample_count, *[g['after_sample'] for g in run.gaps]})
        for left, right in zip(boundaries, boundaries[1:]):
            cuts = [left, *[cut for cut in (planned_cuts or {}).get((run.id,run.manifest_version),
                range(left+CORE_SECONDS*run.sample_rate,right,CORE_SECONDS*run.sample_rate)) if left<cut<right], right]
            for start,end in zip(cuts,cuts[1:]):
                if db.scalar(select(SpeechWindow.id).where(SpeechWindow.run_id == run.id,
                    SpeechWindow.manifest_version == run.manifest_version, SpeechWindow.core_start == start)):
                    continue
                window = SpeechWindow(lecture_id=lecture.id, run_id=run.id, manifest_version=run.manifest_version,
                    core_start=start, core_end=end, context_start=max(left, start-CONTEXT_SECONDS*run.sample_rate),
                    context_end=min(right, end+CONTEXT_SECONDS*run.sample_rate))
                db.add(window); db.flush()
                job = Job(lecture_id=lecture.id, kind='speech.window', logical_key='speech:window:'+window.id,
                    lifecycle_epoch=lecture.lifecycle_epoch, audio_epoch=lecture.audio_epoch, input_revision=window.id)
                db.add(job); db.flush()
                db.add(Outbox(lecture_id=lecture.id, event_type='speech.requested', entity_id=job.id,
                    lifecycle_epoch=lecture.lifecycle_epoch))
                made += 1
    return made


def windows_for(db, lecture):
    return db.execute(select(SpeechWindow, Job, CaptureRun).join(Job, Job.input_revision == SpeechWindow.id)
        .join(CaptureRun, CaptureRun.id == SpeechWindow.run_id)
        .where(SpeechWindow.lecture_id == lecture.id, Job.kind == 'speech.window',
            CaptureRun.audio_epoch == lecture.audio_epoch, CaptureRun.lifecycle_epoch == lecture.lifecycle_epoch,
            SpeechWindow.manifest_version == CaptureRun.manifest_version)
        .order_by(CaptureRun.capture_epoch, SpeechWindow.core_start)).all()


def freeze_transcript(db, lecture):
    """Immutable membership selected while holding the lecture lock."""
    db.flush()
    runs = current_runs(db, lecture)
    windows = windows_for(db, lecture)
    issues = [{'run_id':r.id, **gap} for r in runs for gap in r.gaps]
    manifests = [{'run_id':r.id, 'version':r.manifest_version} for r in runs]
    versions = []
    for window, job, run in windows:
        if job.status != 'completed':
            issues.append({'run_id':run.id, 'reason':'transcription_'+job.status,
                'start_sample':window.core_start, 'end_sample':window.core_end})
        elif window.outcome == 'uncertain':
            issues.append({'run_id':run.id, 'reason':'uncertain_speech',
                'start_sample':window.core_start, 'end_sample':window.core_end})
        versions.extend(db.scalars(select(TranscriptVersion).join(TranscriptSegment,
            TranscriptSegment.id == TranscriptVersion.segment_id).where(
                TranscriptSegment.window_id == window.id,
                TranscriptSegment.current_revision == TranscriptVersion.revision)
            .order_by(TranscriptSegment.position)).all())
    covered_runs = {w.run_id for w, _, _ in windows}
    for run in runs:
        if run.id not in covered_runs and run.final_sample_count != 0:
            issues.append({'run_id':run.id, 'reason':'awaiting_saved_audio'})
    sequence = (db.scalar(select(func.max(TranscriptSnapshot.sequence)).where(TranscriptSnapshot.lecture_id == lecture.id)) or 0)+1
    snapshot = TranscriptSnapshot(lecture_id=lecture.id, sequence=sequence, audio_epoch=lecture.audio_epoch,
        manifests=manifests, issues=issues)
    db.add(snapshot); db.flush()
    for index, version in enumerate(versions):
        db.add(TranscriptSnapshotItem(snapshot_id=snapshot.id, lecture_id=lecture.id, position=index, version_id=version.id))
    lecture.update_seq += 1
    db.add(LectureUpdate(lecture_id=lecture.id, sequence=lecture.update_seq, kind='transcript.changed',
        entity_id=snapshot.id, entity_version=sequence))
    return snapshot


def version_json(db, version):
    segment = db.get(TranscriptSegment, version.segment_id)
    window = db.get(SpeechWindow, segment.window_id)
    run = db.get(CaptureRun, window.run_id)
    return {'id':version.id, 'segment_id':segment.id, 'revision':version.revision,
        'text':version.text, 'author':version.author, 'run_id':run.id, 'segment_number':run.capture_epoch,
        'sample_rate':run.sample_rate, 'start_sample':version.start_sample, 'end_sample':version.end_sample,
        'confidence':version.confidence, 'stability':'stable', 'generation_id':version.generation_id,
        'audio_url':f'/api/lectures/{version.lecture_id}/sources/{version.id}/audio',
        'source_url':f'/api/lectures/{version.lecture_id}/sources/{version.id}'}


def snapshot_json(db, snapshot):
    versions = db.scalars(select(TranscriptVersion).join(TranscriptSnapshotItem,
        TranscriptSnapshotItem.version_id == TranscriptVersion.id)
        .where(TranscriptSnapshotItem.snapshot_id == snapshot.id).order_by(TranscriptSnapshotItem.position)).all()
    return {'id':snapshot.id, 'sequence':snapshot.sequence, 'issues':snapshot.issues,
        'manifests':snapshot.manifests, 'segments':[version_json(db, v) for v in versions]}


def transcript_json(db, lecture):
    snapshot = db.scalar(select(TranscriptSnapshot).where(TranscriptSnapshot.lecture_id == lecture.id)
        .order_by(TranscriptSnapshot.sequence.desc()).limit(1))
    windows = windows_for(db, lecture)
    counts = {state:sum(job.status == state for _, job, _ in windows) for state in ('due','running','completed','failed')}
    runs = current_runs(db, lecture)
    waiting = any(r.final_sample_count != 0 and not any(w.run_id == r.id for w,_,_ in windows) for r in runs)
    if counts['running']: status = 'processing'
    elif counts['due']: status = 'queued'
    elif counts['failed']: status = 'needs_attention'
    elif waiting: status = 'awaiting_saved_audio'
    elif windows: status = 'processed'
    else: status = 'not_started'
    return {'status':status, 'counts':counts, 'waiting_for_audio':waiting,
        'errors':sorted({job.error_code for _,job,_ in windows if job.error_code}),
        'snapshot':snapshot_json(db, snapshot) if snapshot else None,
        'mode':'saved_audio', 'notes_available':db.scalar(select(NoteRevision.id).where(NoteRevision.lecture_id == lecture.id).limit(1)) is not None}


def read_audio(db, store, run, start, end):
    """Read a bounded source range across transport chunks, preserving original sample rate."""
    if start < 0 or end <= start or end-start > 32*run.sample_rate:
        raise ValueError('audio_bounds')
    rows = db.scalars(select(UploadReservation).where(UploadReservation.run_id == run.id,
        UploadReservation.state == 'verified').order_by(UploadReservation.sequence)).all()
    pieces = []; cursor = start
    from .capture import Identity, validate_wav
    for row in rows:
        a = row.identity['start_sample']; b = a+row.identity['sample_count']
        if b <= cursor or a >= end: continue
        if a > cursor: raise ValueError('audio_gap')
        raw = store.read(row.object_key)
        validate_wav(raw, Identity.model_validate(row.identity))
        stop = min(b, end)
        pieces.append(raw[44+(cursor-a)*2:44+(stop-a)*2]); cursor = stop
        if cursor == end: break
    if cursor != end: raise ValueError('audio_gap')
    result = io.BytesIO()
    with wave.open(result, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(run.sample_rate); wav.writeframes(b''.join(pieces))
    return result.getvalue()


class Correction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_version: str | None = None
    text: str = Field(min_length=1, max_length=12000)


def install_transcription(app, current, db_session, owned_lecture, receipt):
    @app.get('/lectures/{lecture_id}/transcript')
    def transcript(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        return transcript_json(db, owned_lecture(db, session.owner_id, lecture_id))

    @app.get('/lectures/{lecture_id}/transcript/snapshots/{snapshot_id}')
    def snapshot(lecture_id: str, snapshot_id: str, session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        row = db.scalar(select(TranscriptSnapshot).where(TranscriptSnapshot.id == snapshot_id,
            TranscriptSnapshot.lecture_id == lecture_id))
        if not row: error(404, 'source_unavailable', 'This transcript revision is unavailable.')
        return snapshot_json(db, row)

    @app.post('/lectures/{lecture_id}/transcription')
    def request_transcription(lecture_id: str, request: Request, session=Depends(current), db=Depends(db_session)):
        mutation(request, session); owned_lecture(db, session.owner_id, lecture_id)
        lecture = lock_lecture(db, lecture_id)
        if lecture.tombstoned: error(404, 'unavailable', 'This lecture is unavailable.')
        # The worker plans pause-aware windows outside request/database locks.
        for _, job, _ in windows_for(db, lecture):
            if job.status == 'failed' or (job.status == 'due' and job.error_code):
                job.status='due'; job.error_code=None; job.attempts=0; job.due_at=now()
        db.commit()
        return transcript_json(db, lecture)

    def source(db, owner, lecture_id, version_id):
        owned_lecture(db, owner, lecture_id)
        version = db.scalar(select(TranscriptVersion).where(TranscriptVersion.id == version_id,
            TranscriptVersion.lecture_id == lecture_id))
        if not version: error(404, 'source_unavailable', 'This source revision is unavailable.')
        return version

    @app.get('/lectures/{lecture_id}/sources/{version_id}')
    def get_source(lecture_id: str, version_id: str, session=Depends(current), db=Depends(db_session)):
        return version_json(db, source(db, session.owner_id, lecture_id, version_id))

    @app.get('/lectures/{lecture_id}/transcript/segments/{segment_id}/versions')
    def history(lecture_id: str, segment_id: str, session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        versions = db.scalars(select(TranscriptVersion).where(TranscriptVersion.lecture_id == lecture_id,
            TranscriptVersion.segment_id == segment_id).order_by(TranscriptVersion.revision)).all()
        if not versions: error(404, 'source_unavailable', 'This passage is unavailable.')
        return [version_json(db, version) for version in versions]

    @app.get('/lectures/{lecture_id}/sources/{version_id}/audio')
    def source_audio(lecture_id: str, version_id: str, request: Request, session=Depends(current), db=Depends(db_session)):
        version = source(db, session.owner_id, lecture_id, version_id)
        segment = db.get(TranscriptSegment, version.segment_id)
        window = db.get(SpeechWindow, segment.window_id)
        run = db.get(CaptureRun, window.run_id)
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        epochs = (lecture.lifecycle_epoch, lecture.audio_epoch)
        if run.audio_epoch != lecture.audio_epoch:
            error(404, 'audio_unavailable', 'Audio was removed; the transcript source remains available.')
        start, end = version.start_sample, version.end_sample
        db.expunge(run); db.rollback()
        try: audio = read_audio(db, app.state.audio_store, run, start, end)
        except Exception: error(503, 'audio_unavailable', 'This audio could not be verified. Try again.')
        db.rollback()
        from .security import authenticate
        authenticate(db, request.cookies.get('nt_session'))
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        if epochs != (lecture.lifecycle_epoch, lecture.audio_epoch):
            error(404, 'audio_unavailable', 'This audio is no longer available.')
        return Response(audio, media_type='audio/wav')

    @app.post('/lectures/{lecture_id}/transcript/segments/{segment_id}/corrections')
    def correct(lecture_id: str, segment_id: str, body: Correction, request: Request,
                session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        if body.expected_version is None: error(428, 'version_required', 'Load the current transcript before correcting it.')
        if not body.text.strip(): error(422, 'invalid_text', 'Enter the corrected words.')
        action = 'correct_transcript:'+segment_id
        existing, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = lock_lecture(db, lecture_id)
        if lecture.tombstoned: error(404, 'unavailable', 'This lecture is unavailable.')
        if existing:
            return version_json(db, source(db, session.owner_id, lecture_id, existing.result_id))
        segment = db.scalar(select(TranscriptSegment).where(TranscriptSegment.id == segment_id,
            TranscriptSegment.lecture_id == lecture_id))
        if not segment: error(404, 'source_unavailable', 'This passage is unavailable.')
        previous = db.scalar(select(TranscriptVersion).where(TranscriptVersion.segment_id == segment_id,
            TranscriptVersion.revision == segment.current_revision))
        if previous.id != body.expected_version:
            error(409, 'transcript_version', 'This passage changed. Your draft is retained; compare it with the latest words.')
        window = db.get(SpeechWindow, segment.window_id)
        run = db.get(CaptureRun, window.run_id)
        if window.manifest_version != run.manifest_version:
            error(409, 'source_changed', 'The audio source changed. Reopen the current transcript before correcting it.')
        segment.current_revision += 1
        version = TranscriptVersion(lecture_id=lecture_id, segment_id=segment_id,
            revision=segment.current_revision, text=body.text.strip(), author='student',
            start_sample=previous.start_sample, end_sample=previous.end_sample,
            confidence={'kind':'unavailable','value':None}, generation_id=previous.generation_id)
        db.add(version); db.flush()
        db.add(CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=version.id))
        freeze_transcript(db, lecture); db.commit()
        return version_json(db, version)
