"""Saved generated question sets, student revisions and separate quality judgments."""
from typing import Literal
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from . import models as m
from .cloud_notes import is_cloud
from .learning import saved_note_context
from .notes import latest
from .note_contract import compact
from .security import error
from .transcription import lock_lecture

QUALITY_KEYS = ('support', 'answerability', 'clarity', 'usefulness')


def review_json(row):
    return {'version': row.version, 'rating': row.rating, 'reviewed_at': row.created_at.isoformat() + 'Z'}


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)


class GenerateInput(Strict):
    revision_id: str = Field(min_length=1, max_length=36)
    preference_id: str = Field(min_length=1, max_length=36)
    prompt: str = Field(min_length=1, max_length=2000)
    cloud_consent: bool = False


class Quality(Strict):
    support: Literal[-1, 0, 1, 2] = -1
    answerability: Literal[-1, 0, 1, 2] = -1
    clarity: Literal[-1, 0, 1, 2] = -1
    usefulness: Literal[-1, 0, 1, 2] = -1


class EditInput(Strict):
    expected_version: int = Field(ge=0)
    question: str = Field(min_length=8, max_length=2000)
    answer: str = Field(min_length=8, max_length=6000)
    quality: Quality = Field(default_factory=Quality)
    feedback: str = Field(default='', max_length=1000)


class AssessmentInput(Strict):
    question_revision: str = Field(min_length=1, max_length=36)
    expected_version: int = Field(ge=0)
    rating: Literal['again', 'developing', 'confident', 'unreviewed']


def job_for(db, row):
    return db.scalar(select(m.Job).where(m.Job.kind == 'learning.generate', m.Job.input_revision == row.id))


def source_current(db, lecture, row):
    deck = saved_note_context(db, lecture)
    if deck['revision_id'] != row.evidence['revision_id']:
        return False
    # Older saved question sets pinned one note block. New flash-card sets pin
    # every eligible block present in the selected note revision.
    block_id = row.evidence.get('block_id')
    if block_id:
        return any(block['id'] == block_id for block in deck['blocks'])
    block_ids = set(row.evidence.get('block_ids', ()))
    return bool(block_ids) and block_ids <= {block['id'] for block in deck['blocks']}


def flashcard_evidence(deck, prompt):
    source_fields = ('id', 'text', 'label', 'source_kind', 'revision_id', 'passage_id',
        'segment_number', 'start_sample', 'end_sample', 'sample_rate')
    sources = {}
    notes = []
    for block in deck['blocks']:
        notes.append({'block_id': block['id'], 'topic': block['topic'], 'passages': block['passages']})
        for source in block['sources']:
            sources.setdefault(source['id'], {key: source[key] for key in source_fields if key in source})
    return {'contract_version': 'flashcards-v1', 'revision_id': deck['revision_id'],
        'block_ids': [block['id'] for block in deck['blocks']], 'topic': 'Flash cards from saved notes',
        'student_prompt': prompt, 'notes': notes, 'sources': list(sources.values()),
        'issues': deck['issues'], 'kind': 'flashcard', 'count': 8}


def summary(db, row):
    job = job_for(db, row)
    pref = db.get(m.NotePreference, row.preference_id)
    return {'id': row.id, 'topic': row.evidence['topic'],
        'prompt': row.evidence.get('student_prompt', row.evidence.get('focus', '')),
        'model': pref.model,
        'status': job.status, 'error_code': job.error_code, 'created_at': row.created_at.isoformat() + 'Z',
        'preview': row.preview if job.status == 'running' else '', 'count': len(row.content or [])}


def selected_question(db, row, question_id):
    original = next((q for q in row.content or [] if q['id'] == question_id), None)
    if not original:
        error(404, 'unavailable', 'This saved question is unavailable.')
    edit = db.scalar(select(m.QuestionEdit).where(m.QuestionEdit.set_id == row.id,
        m.QuestionEdit.question_id == question_id).order_by(m.QuestionEdit.version.desc()).limit(1))
    return original, edit


def question_json(db, row, original, edit):
    revision = edit.id if edit else row.id
    review = db.scalar(select(m.LearningReview).where(m.LearningReview.lecture_id == row.lecture_id,
        m.LearningReview.revision_id == revision, m.LearningReview.block_id == original['id'])
        .order_by(m.LearningReview.version.desc()).limit(1))
    return {**original, 'question': edit.question if edit else original['question'],
        'answer': edit.answer if edit else original['answer'], 'version': edit.version if edit else 0,
        'revision_id': revision, 'student_edited': bool(edit and (edit.question != original['question'] or edit.answer != original['answer'])),
        'quality': edit.quality if edit else dict.fromkeys(QUALITY_KEYS, -1), 'feedback': edit.feedback if edit else '',
        'review': review_json(review) if review else {'version': 0, 'rating': 'unreviewed', 'reviewed_at': None}}


def detail(db, lecture, row):
    questions = [question_json(db, row, *selected_question(db, row, q['id'])) for q in row.content or []]
    return {**summary(db, row), 'revision_id': row.evidence['revision_id'],
        'stale': not source_current(db, lecture, row), 'questions': questions,
        'sources': row.evidence['sources'], 'issues': row.evidence['issues'], 'metadata': row.metadata_json,
        'quality_counts': {'reviewed': sum(all(q['quality'][k] >= 0 for k in QUALITY_KEYS) for q in questions),
            'needs_work': sum(any(q['quality'][k] in (0, 1) for k in QUALITY_KEYS) for q in questions),
            'total': len(questions)}}


def install_questions(app, current, db_session, owned_lecture, receipt):
    def owned(db, session, lecture_id):
        lecture = lock_lecture(db, owned_lecture(db, session.owner_id, lecture_id).id)
        if lecture.tombstoned:
            error(404, 'unavailable', 'This lecture is unavailable.')
        return lecture

    def owned_set(db, lecture_id, set_id):
        row = db.scalar(select(m.QuestionSet).where(m.QuestionSet.id == set_id, m.QuestionSet.lecture_id == lecture_id))
        if not row:
            error(404, 'unavailable', 'This question set is unavailable.')
        return row

    @app.get('/lectures/{lecture_id}/study/questions')
    def sets(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        lecture = owned(db, session, lecture_id)
        deck = saved_note_context(db, lecture)
        pref = latest(db, m.NotePreference, lecture_id, m.NotePreference.version)
        return {'revision_id': deck['revision_id'], 'has_notes': bool(deck['blocks']), 'omitted_blocks': deck['omitted'],
            'preference_id': pref.id if pref else None, 'model': pref.model if pref else None,
            'enabled': bool(pref and pref.enabled), 'cloud': bool(pref and is_cloud(pref.model)),
            'sets': [summary(db, row) for row in db.scalars(select(m.QuestionSet).where(
                m.QuestionSet.lecture_id == lecture_id).order_by(m.QuestionSet.created_at.desc(), m.QuestionSet.id))]}

    @app.post('/lectures/{lecture_id}/study/questions', status_code=202)
    def generate(lecture_id: str, body: GenerateInput, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'questions.generate:' + lecture_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = owned(db, session, lecture_id)
        if prior:
            return summary(db, owned_set(db, lecture_id, prior.result_id))
        pref = latest(db, m.NotePreference, lecture_id, m.NotePreference.version)
        if not pref or not pref.enabled or pref.id != body.preference_id:
            error(409, 'model_changed', 'Choose an enabled note model, then refresh question setup.')
        if is_cloud(pref.model) and not body.cloud_consent:
            error(422, 'cloud_consent_required', 'Confirm sending your saved notes, source text and instructions to the selected cloud model.')
        deck = saved_note_context(db, lecture)
        if not deck['blocks']:
            error(422, 'notes_unavailable', 'Save source-linked notes before generating flash cards.')
        if deck['revision_id'] != body.revision_id:
            error(409, 'notes_changed', 'Saved notes or sources changed. Refresh flash-card setup.')
        if db.scalar(select(m.Job.id).where(m.Job.lecture_id == lecture_id, m.Job.kind == 'learning.generate', m.Job.status.in_(['due', 'running']))):
            error(409, 'questions_pending', 'A question request is already queued or generating for this lecture.')
        if db.scalar(select(func.count()).select_from(m.QuestionSet).where(m.QuestionSet.lecture_id == lecture_id)) >= 100:
            error(422, 'question_set_limit', 'This lecture has reached its 100 saved question-request limit.')
        evidence = flashcard_evidence(deck, body.prompt)
        if len(compact(evidence).encode()) > 16000:
            error(422, 'context_limit', 'Saved notes and source text are too large for one flash-card request. Reduce the saved note context, then try again.')
        settings = latest(db, m.SettingsVersion, lecture_id, m.SettingsVersion.version)
        row = m.QuestionSet(lecture_id=lecture_id, preference_id=pref.id, settings_id=settings.id, evidence=evidence)
        db.add(row); db.flush()
        db.add(m.Job(lecture_id=lecture_id, logical_key='learning:' + row.id, kind='learning.generate',
            lifecycle_epoch=lecture.lifecycle_epoch, audio_epoch=lecture.audio_epoch, input_revision=row.id))
        db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
        db.commit()
        return summary(db, row)

    @app.get('/lectures/{lecture_id}/study/questions/{set_id}')
    def read(lecture_id: str, set_id: str, session=Depends(current), db=Depends(db_session)):
        lecture = owned(db, session, lecture_id)
        return detail(db, lecture, owned_set(db, lecture_id, set_id))

    @app.post('/lectures/{lecture_id}/study/questions/{set_id}/cancel')
    def cancel(lecture_id: str, set_id: str, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'questions.cancel:' + set_id
        prior, key, fingerprint = receipt(db, request, session, action, {})
        owned(db, session, lecture_id)
        row = owned_set(db, lecture_id, set_id)
        if not prior:
            job = job_for(db, row)
            if job.status in ('due', 'running'):
                job.status = 'cancelled'; job.lease_expires_at = None; row.preview = ''
            db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
            db.commit()
        return summary(db, row)

    @app.post('/lectures/{lecture_id}/study/questions/{set_id}/{question_id}/edits')
    def edit(lecture_id: str, set_id: str, question_id: str, body: EditInput, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'questions.edit:' + set_id + ':' + question_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        owned(db, session, lecture_id)
        row = owned_set(db, lecture_id, set_id)
        original, previous = selected_question(db, row, question_id)
        if prior:
            return question_json(db, row, original, db.get(m.QuestionEdit, prior.result_id))
        if body.expected_version != (previous.version if previous else 0):
            error(409, 'question_changed', 'This question changed in another window. Your draft is preserved; load the saved version to compare.')
        revision = m.QuestionEdit(lecture_id=lecture_id, set_id=set_id, question_id=question_id,
            version=body.expected_version + 1, question=body.question, answer=body.answer,
            quality=body.quality.model_dump(), feedback=body.feedback)
        db.add(revision); db.flush()
        db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=revision.id))
        db.commit()
        return question_json(db, row, original, revision)

    @app.get('/lectures/{lecture_id}/study/questions/{set_id}/{question_id}/history')
    def history(lecture_id: str, set_id: str, question_id: str, session=Depends(current), db=Depends(db_session)):
        owned(db, session, lecture_id)
        row = owned_set(db, lecture_id, set_id)
        original, _ = selected_question(db, row, question_id)
        edits = db.scalars(select(m.QuestionEdit).where(m.QuestionEdit.set_id == set_id,
            m.QuestionEdit.question_id == question_id).order_by(m.QuestionEdit.version.desc())).all()
        return [question_json(db, row, original, e) for e in edits] + [question_json(db, row, original, None)]

    @app.post('/lectures/{lecture_id}/study/questions/{set_id}/{question_id}/reviews')
    def assess(lecture_id: str, set_id: str, question_id: str, body: AssessmentInput, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'questions.review:' + set_id + ':' + question_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        lecture = owned(db, session, lecture_id)
        row = owned_set(db, lecture_id, set_id)
        if prior:
            return review_json(db.get(m.LearningReview, prior.result_id))
        card = question_json(db, row, *selected_question(db, row, question_id))
        if not source_current(db, lecture, row) or body.question_revision != card['revision_id'] or body.expected_version != card['review']['version']:
            error(409, 'question_changed', 'Question, sources or assessment changed. Refresh the saved set before assessing again.')
        if any(value in (0, 1) for value in card['quality'].values()) and body.rating != 'unreviewed':
            error(422, 'quality_needs_work', 'Resolve this question’s quality concerns before using it for practice.')
        review = m.LearningReview(lecture_id=lecture_id, revision_id=card['revision_id'], block_id=question_id,
            version=body.expected_version + 1, rating=body.rating)
        db.add(review); db.flush()
        db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=review.id))
        db.commit()
        return review_json(review)
