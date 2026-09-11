"""Saved, source-backed notes and versioned model choices."""
import html
import json
import time
from typing import Literal
from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from .models import (Lecture, SettingsVersion, NotePreference, NoteRequest, NoteRevision, Job,
    TranscriptSnapshot, CommandReceipt, Outbox, now)
from .transcription import lock_lecture, transcript_json, snapshot_json
from .note_provider import OllamaNotes, NoteFailure
from .security import error


def latest(db, model, lecture_id, order):
    return db.scalar(select(model).where(model.lecture_id == lecture_id).order_by(order.desc()).limit(1))


def preference_json(pref):
    return {'version': pref.version, 'model': pref.model, 'digest': pref.model_digest, 'enabled': pref.enabled} if pref else None


def inputs(db, request):
    snapshot = snapshot_json(db, db.get(TranscriptSnapshot, request.snapshot_id))
    settings = db.get(SettingsVersion, request.settings_id)
    from .materials import material_sources
    evidence = {'source_snapshot_id': request.snapshot_id, 'settings_version': settings.version,
        'allow_ai_explanations': settings.ai_explanations,
        'profile': {'depth': settings.depth, 'format': settings.format, 'instructions': settings.instructions, 'detail_prompt': settings.detail_prompt, 'layout_prompt': settings.layout_prompt},
        'sources': [{'id': s['id'], 'text': s['text'], 'start_ms': round(s['start_sample'] * 1000 / s['sample_rate']),
            'end_ms': round(s['end_sample'] * 1000 / s['sample_rate'])} for s in snapshot['segments']] + material_sources(db, settings.material_ids)}
    if request.source_ids is not None:
        ids = set(request.source_ids)
        evidence['sources'] = [s for s in evidence['sources'] if s['id'] in ids]
        if {s['id'] for s in evidence['sources']} != ids: raise ValueError('missing_batch_source')
    return evidence


def revision_json(db, revision):
    request = db.get(NoteRequest, revision.request_id)
    settings = db.get(SettingsVersion, request.settings_id)
    return {'id': revision.id, 'revision': revision.revision, 'content': revision.content,
        'profile': {'depth': settings.depth, 'format': settings.format, 'instructions': settings.instructions, 'detail_prompt': settings.detail_prompt, 'layout_prompt': settings.layout_prompt},
        'resolved_citations': revision.resolved_citations, 'metadata': revision.metadata_json,
        'source_issues': db.get(TranscriptSnapshot, request.snapshot_id).issues,
        'created_at': revision.created_at.isoformat() + 'Z'}


def notes_json(db, lecture):
    pref = latest(db, NotePreference, lecture.id, NotePreference.version)
    revision = latest(db, NoteRevision, lecture.id, NoteRevision.revision)
    snapshot = latest(db, TranscriptSnapshot, lecture.id, TranscriptSnapshot.sequence)
    settings = latest(db, SettingsVersion, lecture.id, SettingsVersion.version)
    request = latest(db, NoteRequest, lecture.id, NoteRequest.created_at)
    job = db.scalar(select(Job).where(Job.kind == 'notes.generate', Job.input_revision == request.id)) if request else None
    current_request = bool(request and pref and snapshot and request.preference_id == pref.id
        and request.snapshot_id == snapshot.id and request.settings_id == settings.id
        and job.lifecycle_epoch == lecture.lifecycle_epoch and job.audio_epoch == lecture.audio_epoch)
    active_request = bool(request and pref and request.preference_id == pref.id and request.settings_id == settings.id
        and job.lifecycle_epoch == lecture.lifecycle_epoch and job.audio_epoch == lecture.audio_epoch)
    stale = bool(revision and (not current_request or revision.request_id != request.id))
    from .materials import material_sources
    present = {s['id'] for s in snapshot_json(db, snapshot)['segments']} if snapshot else set()
    present.update(s['id'] for s in material_sources(db, settings.material_ids))
    covered = {c['source_id'] for c in revision.content['coverage']} if revision else set()
    pending = len(present - covered)
    stale = stale or bool(revision and pending)
    if not pref: status = 'choose_model'
    elif not pref.enabled: status = 'paused'
    elif active_request: status = {'due': 'queued', 'running': 'generating', 'completed': 'ready', 'failed': 'needs_attention', 'cancelled': 'waiting_for_transcript'}[job.status]
    else: status = 'waiting_for_transcript'
    from .note_edits import editing_json
    return {'status': status, 'preference': preference_json(pref), 'stale': stale,
        'editing': editing_json(db, lecture, revision),
        'profile': {'depth': settings.depth, 'format': settings.format, 'instructions': settings.instructions, 'detail_prompt': settings.detail_prompt, 'layout_prompt': settings.layout_prompt},
        'error_code': job.error_code if active_request else None,
        'processing': {'newer_transcript_pending': bool(snapshot and request and request.snapshot_id != snapshot.id),
            'pending_sources': pending, 'saved_sections': len(revision.metadata_json.get('batches', [])) if revision else 0,
            'request_age_seconds': round((now()-request.created_at).total_seconds(),1) if request and job.status in ('due','running') else 0},
        'revision': revision_json(db, revision) if revision else None}


def schedule_notes(db, lecture):
    """Coalesce to the newest snapshot; a running append-only request may finish."""
    pref = latest(db, NotePreference, lecture.id, NotePreference.version)
    if lecture.tombstoned or not pref or not pref.enabled: return None
    transcript = transcript_json(db, lecture)
    snapshot = transcript['snapshot']
    if not snapshot or not snapshot['segments']: return None
    raw_snapshot = db.get(TranscriptSnapshot, snapshot['id'])
    if raw_snapshot.audio_epoch != lecture.audio_epoch: return None
    settings = latest(db, SettingsVersion, lecture.id, SettingsVersion.version)
    revision = latest(db, NoteRevision, lecture.id, NoteRevision.revision)
    prior = db.get(NoteRequest, revision.request_id) if revision else None
    previous_sources = {c['source_id'] for c in revision.content['coverage']} if prior and prior.settings_id == settings.id and prior.preference_id == pref.id else set()
    from .materials import material_sources
    sources = snapshot['segments'] + material_sources(db, settings.material_ids)
    present = {s['id'] for s in sources}
    compatible = bool(prior and prior.settings_id == settings.id and prior.preference_id == pref.id and previous_sources <= present)
    if not previous_sources <= present: previous_sources = set()
    if previous_sources == present and prior.snapshot_id == snapshot['id']: return None
    fresh = [s for s in snapshot['segments'] if s['id'] not in previous_sources]
    # Wait for several short segments (24 seconds of recognized audio windows),
    # or 100 words, before live note work. Flush short tails after capture stops.
    # Corrections and changed preferences bypass the accumulation delay.
    if transcript['mode'] == 'live' and (not revision or compatible):
        from .models import SpeechWindow, TranscriptSegment, TranscriptVersion, CaptureRun
        windows = db.execute(select(SpeechWindow.id, SpeechWindow.core_start, SpeechWindow.core_end, CaptureRun.sample_rate)
            .join(TranscriptSegment, TranscriptSegment.window_id == SpeechWindow.id)
            .join(TranscriptVersion, TranscriptVersion.segment_id == TranscriptSegment.id)
            .join(CaptureRun, CaptureRun.id == SpeechWindow.run_id)
            .where(TranscriptVersion.id.in_([s['id'] for s in fresh])).distinct()).all()
        seconds = sum((end-start)/rate for _, start, end, rate in windows)
        words = sum(len(s['text'].split()) for s in fresh)
        backlog = bool(revision and revision.metadata_json.get('pending_source_count', 0))
        if seconds < 24 and words < 100 and not backlog: return None
    old = db.scalar(select(NoteRequest).where(NoteRequest.snapshot_id == snapshot['id'],
        NoteRequest.preference_id == pref.id, NoteRequest.settings_id == settings.id,
        NoteRequest.base_revision == (revision.revision if revision else 0)))
    if old: return old
    running = db.scalar(select(Job.id).where(Job.lecture_id == lecture.id, Job.kind == 'notes.generate',
        Job.status == 'running', Job.lease_expires_at > now()).limit(1))
    if running: return None
    db.execute(update(Job).where(Job.lecture_id == lecture.id, Job.kind == 'notes.generate',
        Job.status.in_(['due', 'running'])).values(status='cancelled', error_code='superseded'))
    revision = latest(db, NoteRevision, lecture.id, NoteRevision.revision)
    request = NoteRequest(lecture_id=lecture.id, preference_id=pref.id, snapshot_id=snapshot['id'],
        settings_id=settings.id, base_revision=revision.revision if revision else 0,
        source_ids=section_sources(sources, previous_sources))
    db.add(request); db.flush()
    job = Job(lecture_id=lecture.id, kind='notes.generate', logical_key='notes:' + request.id,
        lifecycle_epoch=lecture.lifecycle_epoch, audio_epoch=lecture.audio_epoch, input_revision=request.id)
    db.add(job); db.flush()
    db.add(Outbox(lecture_id=lecture.id, event_type='notes.requested', entity_id=job.id, lifecycle_epoch=lecture.lifecycle_epoch))
    return request


def section_sources(sources, covered):
    """One contextual section per durable revision, including all reused evidence."""
    selected, size, words = set(covered), 0, 0
    pending = [s for s in sources if s['id'] not in covered]
    for source in pending:
        cost = len(source['text'].encode('utf-8'))
        if size and (size + cost > 2400 or words >= 180 or len(selected - covered) >= 8): break
        selected.add(source['id']); size += cost; words += len(source['text'].split())
    return [s['id'] for s in sources if s['id'] in selected]


def markdown(db, lecture, revision):
    # Escape all arbitrary text, including source appendix, so exports cannot inject HTML,
    # links or fence terminators. Code is indented, never interpolated into a fence.
    def escape(value):
        return ''.join('\\' + c if c in '\\`*_{}[]()#+-.!|>' else c for c in html.escape(value, quote=False))
    request = db.get(NoteRequest, revision.request_id)
    snapshot = snapshot_json(db, db.get(TranscriptSnapshot, request.snapshot_id))
    sources = {s['id']: s for s in snapshot['segments']}
    if revision.metadata_json.get('student_revision'):
        from .models import TranscriptVersion
        from .transcription import version_json
        ids = {c['source_id'] for c in revision.content['coverage']}
        ids.update(c['source_id'] for b in revision.content['blocks'] for p in b['passages'] for c in p['sources'])
        sources = {v.id: version_json(db, v) for v in db.scalars(select(TranscriptVersion).where(
            TranscriptVersion.lecture_id == lecture.id, TranscriptVersion.id.in_(ids)))}
    from .materials import material_sources
    material_ids = set(db.get(SettingsVersion, request.settings_id).material_ids)
    if revision.metadata_json.get('student_revision'):
        material_ids.update(c['source_id'].split(':')[1] for c in revision.content['coverage'] if c['source_id'].startswith('material:'))
    sources.update({s['id']: s for s in material_sources(db, sorted(material_ids))})
    cited = list(sources)
    refs = {source: index + 1 for index, source in enumerate(cited)}
    label = 'Student study notes' if revision.metadata_json.get('student_revision') else 'Generated study notes'
    lines = ['# ' + escape(lecture.title), '', f'{label} · Revision {revision.revision}', '',
        'Model: ' + escape(revision.metadata_json['model']), '', 'Check important claims against the sources. Student changes are not AI-verified.', '']
    for block in revision.content['blocks']:
        lines += ['## ' + escape(block['topic']), '']
        if block.get('diagram'):
            from .visual_notes import diagram_description, diagram_stale
            lines += ['AI-created schematic: ' + escape(block['diagram']['caption']), '', escape(diagram_description(block['diagram'])), '']
            if diagram_stale(block):
                lines += ['Review diagram: student changes may no longer match the retained schematic.', '']
        for passage in block['passages']:
            lines.append('Evidence: ' + ('student revision; original source links retained' if passage.get('student_edited') else passage['evidence_kind'].replace('_', ' ')))
            lines.append('')
            lines.extend(['    ' + line for line in passage['text'].splitlines()] if block['kind'] in ('code', 'equation') else [escape(passage['text'])])
            lines += ['', 'Sources: ' + (', '.join(f'[{refs[c["source_id"]]}]' if c['source_id'] in refs else '[unavailable]' for c in passage['sources']) or 'Student addition; no lecture citation'), '']
    omitted = [item for item in revision.content['coverage'] if item['disposition'] != 'used']
    if revision.content['issues'] or snapshot['issues'] or omitted:
        lines += ['## Review needed', '']
        lines.extend('- ' + escape(i['detail']) for i in revision.content['issues'])
        lines.extend('- ' + escape(i['disposition'] + ': ' + i['reason']) + f' (source [{refs.get(i["source_id"], "unavailable")}])' for i in omitted)
        if snapshot['issues']: lines.append('- The transcript has recording or recognition issues; review its source warnings.')
        lines.append('')
    lines += ['## Source appendix', '']
    for source_id in cited:
        s = sources[source_id]
        if s.get('source_kind'):
            lines += [f'### [{refs[source_id]}] Uploaded material: ' + escape(s['label']), '', 'Source version: ' + source_id, '', escape(s['text']), '']
            continue
        lines += [f'### [{refs[source_id]}] Recording {s["segment_number"]}, {s["start_sample"]/s["sample_rate"]:.2f}–{s["end_sample"]/s["sample_rate"]:.2f} seconds',
            '', 'Source version: ' + source_id, '', escape(s['text']), '']
    return '\n'.join(lines)


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_version: int = Field(ge=0)
    model: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    cloud_consent: bool = False
    depth: Literal['detailed', 'standard', 'brief'] | None = None
    format: Literal['topic_outline', 'cornell', 'question_answer'] | None = None
    detail_prompt: str | None = Field(default=None, max_length=2000)
    layout_prompt: str | None = Field(default=None, max_length=2000)
    instructions: str | None = Field(default=None, max_length=1000)


def install_notes(app, current, db_session, owned_lecture, receipt):
    from .cloud_notes import NoteProviders
    app.state.note_provider = NoteProviders(app.state.settings)

    @app.get('/lectures/{lecture_id}/notes/stream')
    def stream(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        from fastapi.responses import StreamingResponse
        from .note_worker import current_input
        from fastapi import HTTPException
        owned_lecture(db, session.owner_id, lecture_id)
        session_id = session.token_hash
        db.rollback()
        def events():
            from .models import Session
            last = None
            while True:
                with app.state.sessions() as connection:
                    try:
                        access = connection.get(Session, session_id)
                        if not access or access.revoked or access.expires_at <= now():
                            yield 'event: expired\ndata: {}\n\n'
                            return
                        lecture = owned_lecture(connection, access.owner_id, lecture_id)
                        request = latest(connection, NoteRequest, lecture_id, NoteRequest.created_at)
                        job = connection.scalar(select(Job).where(Job.kind == 'notes.generate', Job.input_revision == request.id)) if request else None
                        active = bool(job and job.status == 'running' and job.lease_expires_at > now() and current_input(connection, job, lecture))
                        payload = {'attempt': request.preview_attempt if active else '', 'text': request.preview if active else '', 'active': active}
                        if app.state.settings.standalone:
                            from .transcription import transcript_json
                            payload['transcript'] = transcript_json(connection, lecture)
                    except HTTPException as exc:
                        yield ('event: removed\ndata: {}\n\n' if exc.status_code==404 else 'event: expired\ndata: {}\n\n')
                        return
                encoded = json.dumps(payload)
                if encoded != last:
                    yield 'data: ' + encoded + '\n\n'
                    last = encoded
                else:
                    yield ': heartbeat\n\n'
                time.sleep(.25)
        return StreamingResponse(events(), media_type='text/event-stream',
            headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no', 'Content-Encoding': 'identity'})

    from .note_edits import install_edits
    install_edits(app, current, db_session, owned_lecture, receipt)

    @app.get('/note-models')
    def models(session=Depends(current)):
        try: return {'models': app.state.note_provider.models(), 'available': True}
        except NoteFailure: return {'models': [], 'available': False}

    @app.get('/lectures/{lecture_id}/notes')
    def read(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        return notes_json(db, owned_lecture(db, session.owner_id, lecture_id))

    @app.post('/lectures/{lecture_id}/notes/model')
    def choose(lecture_id: str, body: ModelChoice, request: Request, session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        # Check mutation authority before provider I/O; never hold a SQL lock over inference.
        from .security import mutation, authenticate
        mutation(request, session)
        from .cloud_notes import is_cloud
        if body.enabled and is_cloud(body.model) and not body.cloud_consent:
            error(422, 'cloud_consent_required', 'Confirm sending this lecture transcript, selected material text and note prompts to the chosen cloud provider.')
        owner = session.owner_id
        action = 'notes.model:' + lecture_id
        existing, _, _ = receipt(db, request, session, action, body.model_dump())
        if existing: return preference_json(db.get(NotePreference, existing.result_id))
        old = latest(db, NotePreference, lecture_id, NotePreference.version)
        if body.expected_version != (old.version if old else 0): error(409, 'settings_conflict', 'The model choice changed in another window. Refresh and try again.')
        db.rollback()
        if body.enabled:
            try: installed, _ = app.state.note_provider.verify(body.model)
            except NoteFailure: error(503, 'model_unavailable', 'This model or saved connection is unavailable. Refresh models or reconnect the provider.')
        session = authenticate(db, request.cookies.get('nt_session'))
        existing, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = lock_lecture(db, owned_lecture(db, owner, lecture_id).id)
        if existing: return preference_json(db.get(NotePreference, existing.result_id))
        old = latest(db, NotePreference, lecture.id, NotePreference.version)
        if body.expected_version != (old.version if old else 0): error(409, 'settings_conflict', 'The model choice changed in another window. Refresh and try again.')
        if not body.enabled and (not old or body.model != old.model): error(422, 'model_required', 'Choose a model before pausing automatic notes.')
        current_settings = latest(db, SettingsVersion, lecture.id, SettingsVersion.version)
        changes = {key: value for key, value in {'depth': body.depth, 'format': body.format, 'instructions': body.instructions, 'detail_prompt': body.detail_prompt, 'layout_prompt': body.layout_prompt}.items() if value is not None}
        if body.enabled and any(getattr(current_settings, key) != value for key, value in changes.items()):
            fields = {key: getattr(current_settings, key) for key in ('depth', 'format', 'instructions', 'ai_explanations', 'detail_prompt', 'layout_prompt', 'material_ids')}
            db.add(SettingsVersion(lecture_id=lecture.id, version=current_settings.version + 1, **{**fields, **changes}))
            db.flush()
        pref = NotePreference(lecture_id=lecture.id, version=body.expected_version + 1, model=body.model,
            model_digest=installed['digest'] if body.enabled else old.model_digest, enabled=body.enabled)
        db.add(pref); db.flush()
        db.add(CommandReceipt(owner_id=owner, action=action, key=key, fingerprint=fingerprint, result_id=pref.id))
        from .lifecycle import notify
        notify(db,lecture,'notes.preferences',pref.id)
        schedule_notes(db, lecture); db.commit()
        return preference_json(pref)

    @app.post('/lectures/{lecture_id}/notes/retry')
    def retry(lecture_id: str, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'notes.retry:' + lecture_id
        existing, key, fingerprint = receipt(db, request, session, action, {})
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if not existing:
            note_request = schedule_notes(db, lecture)
            if note_request:
                job = db.scalar(select(Job).where(Job.kind == 'notes.generate', Job.input_revision == note_request.id))
                if job.status == 'failed' or (job.status == 'due' and job.error_code):
                    job.status = 'due'; job.error_code = None; job.due_at = now(); job.attempts = 0
            db.add(CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=lecture.id))
            db.commit()
        return notes_json(db, lecture)

    @app.get('/lectures/{lecture_id}/notes/revisions/{revision_id}/export')
    def export(lecture_id: str, revision_id: str, format: Literal['markdown', 'html'] = 'markdown', session=Depends(current), db=Depends(db_session)):
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        revision = db.scalar(select(NoteRevision).where(NoteRevision.id == revision_id, NoteRevision.lecture_id == lecture_id))
        if not revision: error(404, 'unavailable', 'This saved note revision is unavailable.')
        if format == 'html':
            from .visual_notes import html_notes
            return Response(html_notes(lecture.title, revision.content, markdown(db, lecture, revision)), media_type='text/html; charset=utf-8',
                headers={'Content-Disposition': f'attachment; filename="lecture-notes-r{revision.revision}.html"', 'X-Content-Type-Options': 'nosniff'})
        return Response(markdown(db, lecture, revision), media_type='text/markdown; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="lecture-notes-r{revision.revision}.md"', 'X-Content-Type-Options': 'nosniff'})
