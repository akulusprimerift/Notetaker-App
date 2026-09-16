"""Source-linked study views. Bookmarks never change transcript or note history."""
from fastapi import Depends, Request, Query, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from . import models as m
from .security import error
from .transcription import lock_lecture, snapshot_json, saved_through
from .notes import latest


class MarkInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    run_id: str = Field(min_length=1, max_length=36)
    sample: int = Field(ge=0)
    label: str = Field(default='Important to me', min_length=1, max_length=160)


class MarkState(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_version: int = Field(ge=1)
    removed: bool


def mark_json(db, row):
    run = db.get(m.CaptureRun, row.run_id)
    through = saved_through(db, run)
    return {'id': row.id, 'run_id': row.run_id, 'sample': row.sample, 'label': row.label,
        'version': row.version, 'removed': row.removed, 'sample_rate': run.sample_rate,
        'recording_number': run.capture_epoch, 'awaiting_audio': row.sample > through or through == 0}


def catch_up(db, lecture, seconds, run_id=None, end_sample=None):
    snapshot = latest(db, m.TranscriptSnapshot, lecture.id, m.TranscriptSnapshot.sequence)
    response = {'snapshot_id': snapshot.id if snapshot else None, 'revision_id': None,
        'seconds': seconds, 'items': [], 'sources': [], 'issues': [], 'omitted_stale': 0,
        'message': 'No saved transcript yet. Recording and transcription can continue independently.'}
    if not snapshot:
        return response
    sources = snapshot_json(db, snapshot)['segments']
    # version_json provides a stable run/recording identity and original sample range.
    runs = list(db.scalars(select(m.CaptureRun).where(m.CaptureRun.lecture_id == lecture.id).order_by(m.CaptureRun.capture_epoch)))
    if run_id:
        run = next((run for run in runs if run.id == run_id), None)
        if not run:
            error(404, 'unavailable', 'This recording is unavailable.')
    else:
        run = next((run for run in reversed(runs) if any(s['segment_number'] == run.capture_epoch for s in sources)), None)
    if not run:
        return response
    available = [s for s in sources if s['segment_number'] == run.capture_epoch]
    last = max((s['end_sample'] for s in available), default=0)
    end = min(end_sample, last) if end_sample is not None else last
    start = max(0, end - seconds * run.sample_rate)
    recent = [s for s in available if s['start_sample'] < end and s['end_sample'] > start]
    response.update(run_id=run.id, recording_number=run.capture_epoch,
        start_seconds=start / run.sample_rate, end_seconds=end / run.sample_rate,
        issues=snapshot.issues, message='Excerpts from saved notes for this interval. Detailed notes are unchanged.')
    if not recent:
        response['message'] = 'No saved transcript covers this moment yet. Refresh after transcription catches up.'
        return response
    from .note_edits import head
    selected = head(db, lecture.id) or latest(db, m.NoteRevision, lecture.id, m.NoteRevision.revision)
    current = {s['id'] for s in sources}
    recent_ids = {s['id'] for s in recent}
    candidates = []
    material_sources = {}
    if selected:
        response['revision_id'] = selected.id
        for block in selected.content['blocks']:
            for passage in block['passages']:
                citations = {c['source_id'] for c in passage['sources']}
                if not citations.intersection(recent_ids):
                    continue
                # Never present a passage linked to a corrected transcript as current.
                if any(c not in current and not c.startswith('material:') for c in citations):
                    response['omitted_stale'] += 1
                    continue
                try:
                    from .materials import source_for_lecture
                    for ident in citations:
                        if ident.startswith('material:'):
                            material_sources[ident] = source_for_lecture(db, lecture, ident)
                except (HTTPException, ValueError):
                    response['omitted_stale'] += 1
                    continue
                candidates.append({'topic': block['topic'], 'text': passage['text'],
                    'student_edited': bool(passage.get('student_edited')), 'source_ids': sorted(citations),
                    'passage_id': passage['id'], 'kind': 'saved_note'})
    # Use complete passages, never remove a qualification by cutting mid-sentence.
    positions = {s['id']: (s['segment_number'], s['end_sample']) for s in sources}
    candidates.sort(key=lambda item: max(positions[ident] for ident in item['source_ids'] if ident in positions))
    response['items'] = candidates[-4:]
    if not response['items']:
        response['message'] = 'Recent saved transcript excerpts; source-linked notes are not available for this interval yet.'
        response['items'] = [{'topic': 'Recent lecture', 'text': s['text'], 'source_ids': [s['id']],
            'kind': 'transcript', 'student_edited': False, 'passage_id': s['id']} for s in recent[-3:]]
    ids = {ident for item in response['items'] for ident in item['source_ids']}
    response['sources'] = [s for s in sources if s['id'] in ids] + [s for ident, s in material_sources.items() if ident in ids]
    response['awaiting_transcript'] = end_sample is not None and end_sample > last
    response['audio_removed'] = lecture.audio_removed
    response['more_available'] = len(candidates) > 4 or (not candidates and len(recent) > 3)
    return response


def install_study(app, current, db_session, owned_lecture, receipt):
    @app.get('/lectures/{lecture_id}/study/marks')
    def marks(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        return [mark_json(db, row) for row in db.scalars(select(m.ImportantMark).where(
            m.ImportantMark.lecture_id == lecture_id).order_by(m.ImportantMark.created_at, m.ImportantMark.id))]

    @app.post('/lectures/{lecture_id}/study/marks')
    def mark(lecture_id: str, body: MarkInput, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'study.mark:' + lecture_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if lecture.tombstoned:
            error(404, 'unavailable', 'This lecture is unavailable.')
        if prior:
            return mark_json(db, db.get(m.ImportantMark, prior.result_id))
        run = db.scalar(select(m.CaptureRun).where(m.CaptureRun.id == body.run_id, m.CaptureRun.lecture_id == lecture_id))
        if not run or lecture.audio_removed or run.audio_epoch != lecture.audio_epoch:
            error(422, 'recording_unavailable', 'Choose a retained recording from this lecture.')
        if body.sample > 43200 * run.sample_rate or (run.final_sample_count is not None and body.sample > run.final_sample_count):
            error(422, 'timestamp_invalid', 'The marker is outside this recording.')
        if db.scalar(select(func.count()).select_from(m.ImportantMark).where(m.ImportantMark.lecture_id == lecture_id)) >= 500:
            error(422, 'marker_limit', 'This lecture has reached its 500-marker limit.')
        row = m.ImportantMark(lecture_id=lecture_id, run_id=run.id, sample=body.sample, label=body.label.strip() or 'Important to me')
        db.add(row); db.flush()
        db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
        db.commit()
        return mark_json(db, row)

    @app.post('/lectures/{lecture_id}/study/marks/{mark_id}')
    def change_mark(lecture_id: str, mark_id: str, body: MarkState, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'study.mark.state:' + mark_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if lecture.tombstoned:
            error(404, 'unavailable', 'This lecture is unavailable.')
        row = db.scalar(select(m.ImportantMark).where(m.ImportantMark.id == mark_id, m.ImportantMark.lecture_id == lecture_id))
        if not row:
            error(404, 'unavailable', 'This marker is unavailable.')
        if not prior:
            if row.version != body.expected_version:
                error(409, 'marker_changed', 'This marker changed in another window. Refresh before trying again.')
            row.removed = body.removed; row.version += 1
            db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
            db.commit()
        return mark_json(db, row)

    @app.get('/lectures/{lecture_id}/study/catch-up')
    def catchup(lecture_id: str, seconds: int = Query(default=180, ge=30, le=600),
                run_id: str | None = Query(default=None, max_length=36), end_sample: int | None = Query(default=None, ge=0),
                session=Depends(current), db=Depends(db_session)):
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if lecture.tombstoned:
            error(404, 'unavailable', 'This lecture is unavailable.')
        return catch_up(db, lecture, seconds, run_id, end_sample)
