"""Extractive recall practice; no inferred answers or automated mastery claims."""
from typing import Literal
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from . import models as m
from .materials import source_for_lecture
from .note_edits import head
from .notes import latest
from .security import error
from .transcription import lock_lecture, snapshot_json


def review_json(row):
    return {'version': row.version, 'rating': row.rating, 'reviewed_at': row.created_at.isoformat() + 'Z'}


def learning_cards(db, lecture):
    selected = head(db, lecture.id) or latest(db, m.NoteRevision, lecture.id, m.NoteRevision.revision)
    result = {'revision_id': selected.id if selected else None, 'cards': [], 'omitted': 0, 'issues': []}
    if not selected:
        return result
    snapshot = latest(db, m.TranscriptSnapshot, lecture.id, m.TranscriptSnapshot.sequence)
    sources = {s['id']: s for s in snapshot_json(db, snapshot)['segments']} if snapshot else {}
    result['issues'] = selected.content['issues'] + (snapshot.issues if snapshot else [])
    reviews = {}
    for row in db.scalars(select(m.LearningReview).where(m.LearningReview.lecture_id == lecture.id,
            m.LearningReview.revision_id == selected.id).order_by(m.LearningReview.version)):
        reviews[row.block_id] = review_json(row)
    for block in selected.content['blocks']:
        # Keep complete blocks: silently dropping an unsupported qualifier can change an answer.
        passages = block['passages']
        ids = {c['source_id'] for p in passages for c in p['sources']}
        eligible = bool(passages) and all(p['sources'] and p['evidence_kind'] in (
            'exact_quote', 'lecture_paraphrase', 'material_paraphrase') for p in passages)
        for ident in ids:
            if ident.startswith('material:'):
                try:
                    sources[ident] = source_for_lecture(db, lecture, ident)
                except (HTTPException, ValueError):
                    eligible = False
            elif ident not in sources:
                eligible = False
        # A visual exercise cannot be represented faithfully by a text-only card.
        if not eligible or 'diagram' in block:
            result['omitted'] += 1
            continue
        result['cards'].append({'id': block['id'], 'topic': block['topic'],
            'prompt': 'Explain ' + block['topic'] + '. Include the conditions, qualifications and worked steps in your notes.',
            'passages': [{'text': p['text'], 'student_edited': bool(p.get('student_edited'))} for p in passages],
            'sources': [sources[ident] for ident in sorted(ids)],
            'review': reviews.get(block['id'], {'version': 0, 'rating': 'unreviewed', 'reviewed_at': None})})
    return result


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revision_id: str = Field(min_length=1, max_length=36)
    block_id: str = Field(min_length=1, max_length=160)
    expected_version: int = Field(ge=0)
    rating: Literal['again', 'developing', 'confident', 'unreviewed']


def install_learning(app, current, db_session, owned_lecture, receipt):
    def owned_locked(db, session, lecture_id):
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if lecture.tombstoned:
            error(404, 'unavailable', 'This lecture is unavailable.')
        return lecture

    @app.get('/lectures/{lecture_id}/study/learning')
    def cards(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        return learning_cards(db, owned_locked(db, session, lecture_id))

    @app.post('/lectures/{lecture_id}/study/learning/reviews')
    def review(lecture_id: str, body: ReviewInput, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'learning.review:' + lecture_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = owned_locked(db, session, lecture_id)
        if prior:
            return review_json(db.get(m.LearningReview, prior.result_id))
        deck = learning_cards(db, lecture)
        card = next((c for c in deck['cards'] if c['id'] == body.block_id), None)
        if deck['revision_id'] != body.revision_id or not card:
            error(409, 'learning_sources_changed', 'Saved notes or sources changed. Refresh practice before reviewing again.')
        if card['review']['version'] != body.expected_version:
            error(409, 'learning_review_changed', 'This assessment changed in another window. Refresh practice before trying again.')
        row = m.LearningReview(lecture_id=lecture.id, revision_id=body.revision_id,
            block_id=body.block_id, version=body.expected_version + 1, rating=body.rating)
        db.add(row); db.flush()
        db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
        db.commit()
        return review_json(row)
