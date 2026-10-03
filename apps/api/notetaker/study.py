"""Student bookmarks; they never change transcript or note history."""
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from . import models as m
from .security import error
from .transcription import lock_lecture, saved_through


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
