"""Protected student revisions and explicit, version-fenced proposal resolution."""
from copy import deepcopy
from types import SimpleNamespace
from typing import Literal
from uuid import uuid4
from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from .models import (NoteEdit, NoteRevision, NoteRequest, NotePreference, SettingsVersion,
    TranscriptSnapshot, TranscriptSnapshotItem, TranscriptVersion, Job, CommandReceipt, LectureUpdate)
from .security import error
from .transcription import lock_lecture


def head(db, lecture_id):
    return db.scalar(select(NoteEdit).where(NoteEdit.lecture_id == lecture_id).order_by(NoteEdit.version.desc()).limit(1))


def edit_json(db, edit):
    from .notes import revision_json
    base = revision_json(db, db.get(NoteRevision, edit.generated_id))
    resolved = []
    source_ids = {c['source_id'] for b in edit.content['blocks'] for p in b['passages'] for c in p['sources']}
    sources = {v.id: v.text for v in db.scalars(select(TranscriptVersion).where(
        TranscriptVersion.lecture_id == edit.lecture_id, TranscriptVersion.id.in_(source_ids)))}
    from .materials import source_for_lecture
    from .models import Lecture
    for ident in source_ids:
        if ident.startswith('material:'):
            sources[ident] = source_for_lecture(db, db.get(Lecture, edit.lecture_id), ident)['text']
    for block in edit.content['blocks']:
        for passage in block['passages']:
            for citation in passage['sources']:
                text = sources.get(citation['source_id'])
                if text is None: continue
                offset = -1
                for _ in range(citation['occurrence']+1): offset = text.find(citation['quote'], offset+1)
                if offset >= 0:
                    resolved.append({'passage_id': passage['id'], 'source_id': citation['source_id'],
                        'start': offset, 'end': offset+len(citation['quote'])})
    return {**base, 'id': edit.id, 'revision': edit.version, 'content': edit.content,
        'resolved_citations': resolved,
        'student': True, 'action': edit.action, 'generated_id': edit.generated_id,
        'provenance': edit.provenance, 'created_at': edit.created_at.isoformat() + 'Z'}


def proposal_valid(db, lecture, revision):
    from .notes import latest
    request = db.get(NoteRequest, revision.request_id)
    settings = latest(db, SettingsVersion, lecture.id, SettingsVersion.version)
    pref = latest(db, NotePreference, lecture.id, NotePreference.version)
    snapshot = latest(db, TranscriptSnapshot, lecture.id, TranscriptSnapshot.sequence)
    job = db.scalar(select(Job).where(Job.kind == 'notes.generate', Job.input_revision == request.id))
    if (not snapshot or not pref or request.preference_id != pref.id or request.settings_id != settings.id
            or job.lifecycle_epoch != lecture.lifecycle_epoch or job.audio_epoch != lecture.audio_epoch):
        return False
    current = set(db.scalars(select(TranscriptSnapshotItem.version_id).where(TranscriptSnapshotItem.snapshot_id == snapshot.id)))
    from .materials import material_sources
    current.update(s['id'] for s in material_sources(db, settings.material_ids))
    return {c['source_id'] for c in revision.content['coverage']} <= current


def editing_json(db, lecture, generated):
    edit = head(db, lecture.id)
    proposal = generated if edit and generated and generated.id != edit.reviewed_id else None
    from .notes import revision_json
    return {'version': edit.version if edit else 0, 'selected': edit_json(db, edit) if edit else None,
        'proposal': revision_json(db, proposal) if proposal else None,
        'proposal_valid': proposal_valid(db, lecture, proposal) if proposal else False,
        'sources_changed': any(not proposal_valid(db, lecture, db.get(NoteRevision, ident)) for ident in edit.provenance) if edit else False}


class Patch(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=12000)


class EditCommand(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_version: int = Field(ge=0)
    base_id: str = Field(min_length=1, max_length=36)
    action: Literal['save', 'keep', 'replace', 'merge', 'undo']
    proposal_id: str | None = Field(default=None, max_length=36)
    target_id: str | None = Field(default=None, max_length=36)
    passages: list[Patch] = Field(default_factory=list, max_length=10000)
    topics: list[Patch] = Field(default_factory=list, max_length=10000)
    block_ids: list[str] = Field(default_factory=list, max_length=10000)
    additional_text: str = Field(default='', max_length=12000)


def install_edits(app, current, db_session, owned_lecture, receipt):
    @app.get('/lectures/{lecture_id}/notes/history')
    def history(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        owned_lecture(db, session.owner_id, lecture_id)
        edits = db.execute(select(NoteEdit.id, NoteEdit.version, NoteEdit.action).where(
            NoteEdit.lecture_id == lecture_id).order_by(NoteEdit.version.desc())).all()
        generated = db.execute(select(NoteRevision.id, NoteRevision.revision).where(
            NoteRevision.lecture_id == lecture_id).order_by(NoteRevision.revision.desc())).all()
        return {'edits': [{'id': e.id, 'version': e.version, 'action': e.action} for e in edits],
            'generated': [{'id': r.id, 'version': r.revision} for r in generated]}

    @app.post('/lectures/{lecture_id}/notes/edits')
    def write(lecture_id: str, body: EditCommand, request: Request, session=Depends(current), db=Depends(db_session)):
        from .notes import latest
        action = 'notes.edit:' + lecture_id
        existing, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if existing:
            return edit_json(db, db.get(NoteEdit, existing.result_id))
        selected = head(db, lecture_id)
        generated = latest(db, NoteRevision, lecture_id, NoteRevision.revision)
        base = selected or generated
        if not base: error(409, 'notes_required', 'Wait for saved notes before editing.')
        if body.expected_version != (selected.version if selected else 0) or body.base_id != base.id:
            error(409, 'notes_conflict', 'The saved notes changed in another window. Your draft is kept. Compare it with the latest copy before saving again.')
        content = deepcopy(base.content)
        generated_id = selected.generated_id if selected else generated.id
        reviewed_id = selected.reviewed_id if selected else generated.id
        provenance = list(selected.provenance) if selected else [generated.id]
        if body.action == 'save':
            passages = {p['id']: p for b in content['blocks'] for p in b['passages']}
            topics = {b['id']: b for b in content['blocks']}
            for patches, targets, field, limit in ((body.passages, passages, 'text', 12000), (body.topics, topics, 'topic', 200)):
                if len({p.id for p in patches}) != len(patches): error(422, 'duplicate_patch', 'Each passage can be edited once.')
                for patch in patches:
                    if patch.id not in targets or not patch.text.strip() or len(patch.text) > limit:
                        error(422, 'invalid_edit', 'An edited heading or passage is unavailable, empty or too long.')
                    if targets[patch.id][field] != patch.text:
                        targets[patch.id][field] = patch.text
                        targets[patch.id]['student_edited'] = True
            if body.additional_text.strip():
                ident = 'student-' + str(uuid4())
                content['blocks'].append({'id': ident, 'topic': 'My additions', 'kind': 'explanation',
                    'student_edited': True, 'passages': [{'id': ident + '-p', 'text': body.additional_text,
                        'evidence_kind': 'student_note', 'student_edited': True, 'sources': []}]})
        elif body.action in ('keep', 'replace', 'merge'):
            if not generated or body.proposal_id != generated.id or not proposal_valid(db, lecture, generated):
                error(409, 'proposal_changed', 'This suggestion changed or its sources or preferences are outdated. Refresh the comparison before resolving it.')
            reviewed_id = generated.id
            if body.action == 'replace':
                content = deepcopy(generated.content); generated_id = generated.id; provenance = [generated.id]
            elif body.action == 'merge':
                blocks = {b['id']: b for b in generated.content['blocks']}
                if not body.block_ids or len(set(body.block_ids)) != len(body.block_ids) or any(b not in blocks for b in body.block_ids):
                    error(422, 'invalid_merge', 'Choose one or more sections from this suggestion.')
                # Keep all current student prose; append explicitly selected suggestion sections.
                for ident in body.block_ids:
                    block = deepcopy(blocks[ident]); block['id'] = 'merge-' + str(uuid4())
                    for index, passage in enumerate(block['passages']): passage['id'] = block['id'] + f'-p{index}'
                    content['blocks'].append(block)
                old = {c['source_id'] for c in content['coverage']}
                content['coverage'].extend(deepcopy([c for c in generated.content['coverage'] if c['source_id'] not in old]))
                content['issues'].extend(deepcopy(generated.content['issues']))
                provenance = list(dict.fromkeys([*provenance, generated.id]))
        else:
            target = db.scalar(select(NoteEdit).where(NoteEdit.id == body.target_id, NoteEdit.lecture_id == lecture_id))
            target_generated = db.scalar(select(NoteRevision).where(NoteRevision.id == body.target_id, NoteRevision.lecture_id == lecture_id))
            if target:
                content = deepcopy(target.content); generated_id = target.generated_id
                provenance = list(target.provenance); reviewed_id = target.reviewed_id
            elif target_generated:
                content = deepcopy(target_generated.content); generated_id = target_generated.id
                provenance = [target_generated.id]; reviewed_id = target_generated.id
            else: error(404, 'revision_unavailable', 'This earlier revision is unavailable.')
        if body.action == 'merge':
            cited = {c['source_id'] for b in content['blocks'] for p in b['passages'] for c in p['sources']}
            for entry in content['coverage']:
                if entry['source_id'] in cited:
                    entry.update(disposition='used', reason='Referenced by the selected notes.')
                elif entry['disposition'] == 'used':
                    entry.update(disposition='omitted', reason='This source was not included in the selected sections; review it for missing detail.')
        edit = NoteEdit(lecture_id=lecture_id, version=body.expected_version+1, generated_id=generated_id,
            reviewed_id=reviewed_id, content=content, provenance=provenance, action=body.action)
        db.add(edit); db.flush()
        lecture.update_seq += 1
        db.add(LectureUpdate(lecture_id=lecture_id, sequence=lecture.update_seq, kind='notes.edited', entity_id=edit.id, entity_version=edit.version))
        db.add(CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=edit.id))
        db.commit()
        return edit_json(db, edit)

    @app.get('/lectures/{lecture_id}/notes/edits/{edit_id}/export')
    def export(lecture_id: str, edit_id: str, session=Depends(current), db=Depends(db_session)):
        from .notes import markdown
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        edit = db.scalar(select(NoteEdit).where(NoteEdit.id == edit_id, NoteEdit.lecture_id == lecture_id))
        if not edit: error(404, 'revision_unavailable', 'This saved student revision is unavailable.')
        base = db.get(NoteRevision, edit.generated_id)
        revision = SimpleNamespace(request_id=base.request_id, revision=edit.version, content=edit.content,
            metadata_json={**base.metadata_json, 'student_revision': True})
        return Response(markdown(db, lecture, revision), media_type='text/markdown; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="lecture-notes-student-{edit.version}.md"', 'X-Content-Type-Options': 'nosniff'})
