"""Capture admission, fenced uploads and recovery. Speech execution belongs to M03."""
import hashlib
import io
import json
import wave
from datetime import timedelta
from hmac import compare_digest
from typing import Literal
from uuid import uuid4

from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select, update
from starlette.concurrency import run_in_threadpool

from .models import (Lecture, CaptureRun, UploadReservation, AudioChunk, AudioManifestRevision,
    CommandReceipt, Job, Outbox, LectureUpdate, now)
from .security import mutation, digest, error, authenticate

MAX_CHUNK = 8 * 1024 * 1024
GRANT_SECONDS = 45


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Start(Input):
    run_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
    sample_rate: int = Field(ge=8000, le=192000)
    grant: str = Field(min_length=32, max_length=100)
    expected_capture_epoch: int = Field(ge=0)


class Gap(Input):
    reason: Literal['microphone_lost', 'sleep_or_suspension', 'storage_failure', 'crash', 'takeover', 'between_runs']
    after_sample: int = Field(ge=0, le=2**40)
    unknown_extent: Literal[True] = True


class Seal(Input):
    expected_version: int | None = Field(default=None, ge=0)
    last_sequence: int = Field(ge=-1, le=100000)
    final_sample_count: int = Field(ge=0, le=2**40)
    gaps: list[Gap] = Field(default_factory=list, max_length=100)


class Recovery(Seal):
    interrupted: bool = True
    run_id: str = Field(min_length=36, max_length=36)
    grant: str = Field(min_length=32, max_length=100)
    expected_capture_epoch: int = Field(ge=0)


class Identity(Input):
    run_id: str = Field(min_length=36, max_length=36)
    capture_epoch: int = Field(ge=1)
    sequence: int = Field(ge=0, le=100000)
    start_sample: int = Field(ge=0, le=2**40)
    sample_count: int = Field(ge=1, le=MAX_CHUNK//2)
    sample_rate: int = Field(ge=8000, le=192000)
    channels: Literal[1] = 1
    encoding: Literal['pcm_s16le_wav'] = 'pcm_s16le_wav'
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    byte_length: int = Field(ge=46, le=MAX_CHUNK)


def validate_wav(data, identity):
    if len(data) != identity.byte_length or hashlib.sha256(data).hexdigest() != identity.sha256:
        error(422, 'audio_mismatch', 'The audio length or checksum does not match. Keep the local copy.')
    try:
        # Restrict transport to the canonical PCM header produced by our worker.
        if len(data) != 44 + identity.sample_count * 2 or data[:4] != b'RIFF' or data[8:16] != b'WAVEfmt ' or data[36:40] != b'data':
            raise ValueError('header')
        if int.from_bytes(data[4:8], 'little') != len(data)-8 or int.from_bytes(data[16:20], 'little') != 16 or int.from_bytes(data[40:44], 'little') != len(data)-44:
            raise ValueError('length')
        if int.from_bytes(data[28:32], 'little') != identity.sample_rate*2 or int.from_bytes(data[32:34], 'little') != 2:
            raise ValueError('alignment')
        with wave.open(io.BytesIO(data), 'rb') as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes(), audio.getcomptype()) != (1, 2, identity.sample_rate, identity.sample_count, 'NONE'):
                raise ValueError('format')
            if len(audio.readframes(identity.sample_count)) != identity.sample_count * 2:
                raise ValueError('truncated')
    except (wave.Error, EOFError, ValueError):
        error(422, 'audio_format', 'This audio chunk has an invalid PCM WAV format. Keep the local copy.')


def install_capture(app, current, db_session, owned_lecture, receipt):
    def merged_gaps(existing, incoming):
        result = list(existing)
        for gap in incoming:
            if gap not in result:
                result.append(gap)
        return result

    def lock(db, owner, lecture_id):
        owned_lecture(db, owner, lecture_id)
        if db.bind.dialect.name == 'sqlite':
            db.execute(update(Lecture).where(Lecture.id == lecture_id).values(update_seq=Lecture.update_seq))
        lecture = db.scalar(select(Lecture).where(Lecture.id == lecture_id).with_for_update().execution_options(populate_existing=True))
        if lecture.tombstoned:
            error(404, 'unavailable', 'This lecture is unavailable.')
        return lecture

    def run_for(db, lecture, run_id):
        run = db.scalar(select(CaptureRun).where(CaptureRun.id == run_id, CaptureRun.lecture_id == lecture.id))
        if not run or run.lifecycle_epoch != lecture.lifecycle_epoch or run.audio_epoch != lecture.audio_epoch:
            error(404, 'unavailable', 'This recording is unavailable.')
        return run

    def grant(request, lecture, run, allow_expired=False):
        if lecture.audio_removed or lecture.status in ('finalizing','finalized'):
            error(409,'capture_closed','This lecture no longer accepts audio. Start a new lecture to record.')
        token = request.headers.get('x-capture-grant', '')
        if not compare_digest(digest(token), run.grant_hash):
            error(409, 'capture_grant', 'This recording needs recovery before it can save more audio.')
        if not run.recovery and run.capture_epoch != lecture.capture_epoch:
            error(409, 'capture_fenced', 'Another recording has taken over. Stop here and recover this segment.')
        if run.state == 'interrupted':
            error(409, 'capture_interrupted', 'Recover this interrupted recording before uploading.')
        if not allow_expired and run.grant_expires_at <= now():
            error(409, 'capture_expired', 'Renew this recording connection before saving more audio.')

    def notify(db, lecture, kind, entity_id, version):
        lecture.update_seq += 1
        db.add(LectureUpdate(lecture_id=lecture.id, sequence=lecture.update_seq, kind=kind, entity_id=entity_id, entity_version=version))
        db.add(Outbox(lecture_id=lecture.id, event_type=kind, entity_id=entity_id, lifecycle_epoch=lecture.lifecycle_epoch))

    def manifest(db, run):
        rows = db.scalars(select(UploadReservation).where(UploadReservation.run_id == run.id).order_by(UploadReservation.sequence)).all()
        chunks = [dict(row.identity, chunk_id=row.id, storage_state=row.state) for row in rows]
        through = sequence = 0
        for row in rows:
            identity = row.identity
            if row.state != 'verified' or row.sequence != sequence or identity['start_sample'] != through:
                break
            through += identity['sample_count']
            sequence += 1
        sealed = run.last_sequence is not None
        complete = sealed and sequence == run.last_sequence + 1 and through == run.final_sample_count
        return {'id':run.id, 'lecture_id':run.lecture_id, 'capture_epoch':run.capture_epoch, 'sample_rate':run.sample_rate,
            'state':run.state, 'recovery':run.recovery, 'manifest_version':run.manifest_version,
            'last_sequence':run.last_sequence, 'final_sample_count':run.final_sample_count, 'gaps':run.gaps,
            'chunks':chunks, 'saved_through_samples':through, 'complete':complete, 'sealed':sealed,
            'grant_seconds':GRANT_SECONDS, 'created_at':run.created_at.isoformat()+'Z'}

    def seal_bounds(db, run, body):
        if (body.last_sequence == -1) != (body.final_sample_count == 0):
            error(422, 'seal_bounds', 'The final audio count does not match the recording manifest.')
        if any(gap.after_sample > body.final_sample_count for gap in body.gaps):
            error(422, 'gap_bounds', 'An interruption is outside this recording segment.')
        for row in db.scalars(select(UploadReservation).where(UploadReservation.run_id == run.id)):
            end = row.identity['start_sample'] + row.identity['sample_count']
            if row.sequence > body.last_sequence or end > body.final_sample_count or (row.sequence == body.last_sequence and end != body.final_sample_count):
                error(409, 'seal_conflict', 'Saved or pending audio extends beyond this manifest. Keep both copies for recovery.')

    def freeze(db, run):
        db.flush()
        result = manifest(db, run)
        db.add(AudioManifestRevision(lecture_id=run.lecture_id, run_id=run.id, version=run.manifest_version, content=result))
        return result

    def update_capture_status(db, lecture):
        db.flush()
        runs = db.scalars(select(CaptureRun).where(CaptureRun.lecture_id == lecture.id,
            CaptureRun.lifecycle_epoch == lecture.lifecycle_epoch, CaptureRun.audio_epoch == lecture.audio_epoch)).all()
        if any(run.state == 'recording' for run in runs):
            lecture.status = 'recording'
        else:
            lecture.status = 'audio_saved' if runs and all(manifest(db, run)['complete'] for run in runs) else 'audio_pending'

    def acquire(body, request, session, db, takeover):
        if not app.state.audio_store.available:
            error(503, 'capture_unavailable', 'Audio storage is not configured. Recording has not started.')
        # Readiness check before taking any write lock.
        db.commit()
        try:
            app.state.audio_store.ready()
        except Exception:
            error(503, 'audio_unavailable', 'Audio storage is unavailable. Recording has not started.')
        action = ('capture_takeover:' if takeover else 'capture_start:') + request.path_params['lecture_id']
        existing, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = lock(db, session.owner_id, request.path_params['lecture_id'])
        if existing:
            return manifest(db, run_for(db, lecture, existing.result_id))
        if lecture.audio_removed or lecture.status in ('finalizing','finalized'):
            error(409,'capture_closed','This lecture no longer accepts audio. Start a new lecture to record.')
        if lecture.capture_epoch != body.expected_capture_epoch:
            error(409, 'capture_version', 'Recording ownership changed. Refresh before starting.')
        active = db.scalar(select(CaptureRun).where(CaptureRun.lecture_id == lecture.id, CaptureRun.state == 'recording'))
        if active and not takeover:
            error(409, 'capture_owned', 'A recording is already open. Recover it or explicitly take over.')
        if takeover and not active:
            error(409, 'capture_version', 'There is no active recording to take over. Refresh this lecture.')
        if active:
            active.state = 'interrupted'
            active.manifest_version += 1
            active.gaps = [*active.gaps, {'reason':'takeover','after_sample':manifest(db, active)['saved_through_samples'],'unknown_extent':True}]
        lecture.capture_epoch += 1
        run = CaptureRun(id=body.run_id or str(uuid4()), lecture_id=lecture.id, capture_epoch=lecture.capture_epoch, lifecycle_epoch=lecture.lifecycle_epoch,
            audio_epoch=lecture.audio_epoch, grant_hash=digest(body.grant), grant_expires_at=now()+timedelta(seconds=GRANT_SECONDS), sample_rate=body.sample_rate,
            gaps=[{'reason':'between_runs','after_sample':0,'unknown_extent':True}] if lecture.capture_epoch > 1 else [])
        db.add(run)
        db.flush()
        lecture.status = 'recording'
        db.add(CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=run.id))
        notify(db, lecture, 'capture.started', run.id, run.manifest_version)
        db.commit()
        return manifest(db, run)

    @app.get('/lectures/{lecture_id}/capture')
    def capture_status(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        lecture = lock(db, session.owner_id, lecture_id)
        runs = db.scalars(select(CaptureRun).where(CaptureRun.lecture_id == lecture.id).order_by(CaptureRun.capture_epoch)).all()
        return {'available':app.state.audio_store.available and not lecture.audio_removed and lecture.status not in ('finalizing','finalized'), 'capture_epoch':lecture.capture_epoch, 'runs':[manifest(db, run) for run in runs], 'processing':'saved_audio'}

    @app.post('/lectures/{lecture_id}/capture-runs', status_code=201)
    def start(lecture_id: str, body: Start, request: Request, session=Depends(current), db=Depends(db_session)):
        mutation(request, session)
        owned_lecture(db, session.owner_id, lecture_id)
        return acquire(body, request, session, db, False)

    @app.post('/lectures/{lecture_id}/capture-takeover', status_code=201)
    def takeover(lecture_id: str, body: Start, request: Request, session=Depends(current), db=Depends(db_session)):
        mutation(request, session)
        owned_lecture(db, session.owner_id, lecture_id)
        return acquire(body, request, session, db, True)

    @app.post('/lectures/{lecture_id}/capture-runs/{run_id}/heartbeat')
    def heartbeat(lecture_id: str, run_id: str, request: Request, session=Depends(current), db=Depends(db_session)):
        mutation(request, session)
        lecture = lock(db, session.owner_id, lecture_id)
        run = run_for(db, lecture, run_id)
        grant(request, lecture, run, allow_expired=True)
        run.heartbeat_at = now()
        run.grant_expires_at = now()+timedelta(seconds=GRANT_SECONDS)
        db.commit()
        return {'grant_seconds':GRANT_SECONDS}

    @app.get('/lectures/{lecture_id}/capture-runs/{run_id}/manifest')
    def get_manifest(lecture_id: str, run_id: str, session=Depends(current), db=Depends(db_session)):
        lecture = lock(db, session.owner_id, lecture_id)
        return manifest(db, run_for(db, lecture, run_id))

    def save_chunk(lecture_id, run_id, sequence, identity, data, request, db):
        # Reauthenticate after the bounded body read, then reserve before external IO.
        db.expire_all()
        session = authenticate(db, request.cookies.get('nt_session'))
        mutation(request, session)
        lecture = lock(db, session.owner_id, lecture_id)
        run = run_for(db, lecture, run_id)
        grant(request, lecture, run)
        if identity.run_id != run_id or identity.sequence != sequence or identity.capture_epoch != run.capture_epoch or identity.sample_rate != run.sample_rate:
            error(409, 'chunk_identity', 'The audio identity does not match this recording.')
        if sequence == 0 and identity.start_sample != 0:
            error(409, 'chunk_range', 'The first audio chunk must start at sample zero.')
        end = identity.start_sample + identity.sample_count
        if run.last_sequence is not None and (sequence > run.last_sequence or end > run.final_sample_count or (sequence == run.last_sequence and end != run.final_sample_count)):
            error(409, 'sealed_bounds', 'This audio lies outside the sealed recording.')
        payload = identity.model_dump()
        row = db.scalar(select(UploadReservation).where(UploadReservation.run_id == run_id, UploadReservation.sequence == sequence))
        if row and row.identity != payload:
            error(409, 'chunk_conflict', 'This chunk number already refers to different audio. Keep the local copy.')
        if not row:
            others = db.scalars(select(UploadReservation).where(UploadReservation.run_id == run_id)).all()
            for other in others:
                start_other = other.identity['start_sample']
                end_other = start_other + other.identity['sample_count']
                if (sequence < other.sequence and end > start_other) or (sequence > other.sequence and identity.start_sample < end_other):
                    error(409, 'chunk_overlap', 'These audio ranges overlap or disagree with their order.')
                if (sequence+1 == other.sequence and end != start_other) or (other.sequence+1 == sequence and end_other != identity.start_sample):
                    error(409, 'chunk_gap', 'Adjacent audio chunks are not contiguous. Recover the interruption explicitly.')
            row = UploadReservation(lecture_id=lecture_id, run_id=run_id, sequence=sequence, identity=payload,
                object_key=f'{lecture_id}/{run_id}/{sequence}/{identity.sha256}.wav')
            db.add(row)
            db.flush()
        row_id, object_key = row.id, row.object_key
        if row.state == 'verified':
            return dict(payload, chunk_id=row.id, storage_state='verified', manifest_version=run.manifest_version)
        db.commit()
        try:
            app.state.audio_store.write_verified(object_key, data, identity.sha256)
        except Exception:
            error(503, 'audio_save_failed', 'Audio has not been confirmed saved. Keep this page open; its local copy can retry.')
        # Fresh lock and epochs fence an upload that finished after takeover/deletion.
        db.expire_all()
        session = authenticate(db, request.cookies.get('nt_session'))
        lecture = lock(db, session.owner_id, lecture_id)
        run = run_for(db, lecture, run_id)
        grant(request, lecture, run)
        row = db.get(UploadReservation, row_id)
        if row.state != 'verified':
            row.state = 'verified'
            run.manifest_version += 1
            db.add(AudioChunk(id=row.id, lecture_id=lecture.id))
            job = Job(lecture_id=lecture.id, logical_key='speech:chunk:'+row.id, kind='speech.chunk',
                lifecycle_epoch=lecture.lifecycle_epoch, audio_epoch=lecture.audio_epoch, input_revision=row.id)
            db.add(job)
            db.flush()
            notify(db, lecture, 'audio.verified', job.id, run.manifest_version)
            if run.last_sequence is not None:
                freeze(db, run)
                update_capture_status(db, lecture)
        db.commit()
        return dict(payload, chunk_id=row.id, storage_state='verified', manifest_version=run.manifest_version)

    @app.put('/lectures/{lecture_id}/capture-runs/{run_id}/chunks/{sequence}')
    async def upload(lecture_id: str, run_id: str, sequence: int, request: Request, session=Depends(current), db=Depends(db_session)):
        mutation(request, session)
        owned_lecture(db, session.owner_id, lecture_id)
        meta = request.headers.get('x-chunk-identity', '')
        if len(meta) > 2048:
            error(422, 'chunk_identity', 'Audio metadata is too large.')
        try:
            identity = Identity.model_validate_json(meta)
        except ValidationError:
            error(422, 'chunk_identity', 'Audio metadata is invalid.')
        data = bytearray()
        async for part in request.stream():
            if len(data)+len(part) > MAX_CHUNK:
                error(413, 'chunk_too_large', 'This audio chunk exceeds the upload limit.')
            data.extend(part)
        validate_wav(data, identity)
        return await run_in_threadpool(save_chunk, lecture_id, run_id, sequence, identity, bytes(data), request, db)

    @app.post('/lectures/{lecture_id}/capture-runs/{run_id}/seal')
    def seal(lecture_id: str, run_id: str, body: Seal, request: Request, session=Depends(current), db=Depends(db_session)):
        mutation(request, session)
        if body.expected_version is None:
            error(428, 'version_required', 'Refresh the recording manifest before sealing.')
        lecture = lock(db, session.owner_id, lecture_id)
        run = run_for(db, lecture, run_id)
        grant(request, lecture, run)
        gaps = merged_gaps(run.gaps, body.model_dump()['gaps'])
        if run.last_sequence is not None:
            if (run.last_sequence, run.final_sample_count, run.gaps) == (body.last_sequence, body.final_sample_count, gaps):
                return manifest(db, run)
            error(409, 'seal_conflict', 'This recording already has a different sealed manifest.')
        if body.expected_version != run.manifest_version:
            error(409, 'manifest_version', 'Audio save progress changed. Refresh the manifest and retry sealing.')
        seal_bounds(db, run, body)
        run.last_sequence, run.final_sample_count, run.gaps = body.last_sequence, body.final_sample_count, gaps
        run.state = 'stopped'
        run.manifest_version += 1
        result = freeze(db, run)
        update_capture_status(db, lecture)
        notify(db, lecture, 'capture.stopped', run.id, run.manifest_version)
        from .transcription import freeze_transcript
        freeze_transcript(db, lecture)
        db.commit()
        return result

    @app.post('/lectures/{lecture_id}/capture-recovery')
    def recover(lecture_id: str, body: Recovery, request: Request, session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        if body.expected_version is None:
            error(428, 'version_required', 'Refresh the recording manifest before recovery.')
        existing, key, fingerprint = receipt(db, request, session, 'capture_recovery:'+lecture_id, body.model_dump())
        lecture = lock(db, session.owner_id, lecture_id)
        run = run_for(db, lecture, body.run_id)
        if existing:
            return manifest(db, run)
        if lecture.audio_removed or lecture.status in ('finalizing','finalized'):
            error(409,'capture_closed','This lecture no longer accepts recovered audio.')
        if body.expected_capture_epoch != lecture.capture_epoch or body.expected_version != run.manifest_version:
            error(409, 'recovery_version', 'Recording state changed. Refresh before recovery.')
        seal_bounds(db, run, body)
        if run.last_sequence is not None and (run.last_sequence != body.last_sequence or run.final_sample_count != body.final_sample_count):
            error(409, 'recovery_bounds', 'Recovery cannot silently change a sealed recording boundary.')
        if run.state == 'recording' and lecture.capture_epoch == run.capture_epoch:
            lecture.capture_epoch += 1
            lecture.status = 'audio_pending'
        run.last_sequence, run.final_sample_count = body.last_sequence, body.final_sample_count
        run.gaps = merged_gaps(run.gaps, body.model_dump()['gaps'])
        if body.interrupted and not any(g['reason'] == 'crash' for g in run.gaps) and run.state != 'stopped':
            run.gaps = [*run.gaps, {'reason':'crash', 'after_sample':body.final_sample_count, 'unknown_extent':True}]
        run.state, run.recovery = 'stopped', True
        run.grant_hash = digest(body.grant)
        run.grant_expires_at = now()+timedelta(seconds=GRANT_SECONDS)
        run.manifest_version += 1
        result = freeze(db, run)
        update_capture_status(db, lecture)
        db.add(CommandReceipt(owner_id=session.owner_id, action='capture_recovery:'+lecture_id, key=key, fingerprint=fingerprint, result_id=run.id))
        notify(db, lecture, 'capture.recovered', run.id, run.manifest_version)
        from .transcription import freeze_transcript
        freeze_transcript(db, lecture)
        db.commit()
        return result

    @app.get('/lectures/{lecture_id}/audio-chunks/{chunk_id}')
    def read_audio(lecture_id: str, chunk_id: str, request: Request, session=Depends(current), db=Depends(db_session)):
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        row = db.scalar(select(UploadReservation).join(AudioChunk, AudioChunk.id == UploadReservation.id).where(UploadReservation.id == chunk_id, UploadReservation.lecture_id == lecture_id))
        if not row:
            error(404, 'audio_unavailable', 'This audio is unavailable.')
        run_for(db, lecture, row.run_id)
        key, checksum, size = row.object_key, row.identity['sha256'], row.identity['byte_length']
        db.commit()
        try:
            data = app.state.audio_store.read(key)
            if len(data) != size or hashlib.sha256(data).hexdigest() != checksum:
                raise ValueError('readback')
        except Exception:
            error(503, 'audio_unavailable', 'This saved audio could not be read. Try again.')
        db.expire_all()
        session = authenticate(db, request.cookies.get('nt_session'))
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        run_for(db, lecture, row.run_id)
        return Response(data, media_type='audio/wav', headers={'Content-Disposition':'inline; filename="lecture-segment.wav"'})
