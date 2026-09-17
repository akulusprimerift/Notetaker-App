from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from sqlalchemy import select, func
from test_workspace import setup, course, lecture
from test_capture import capture
from test_transcription import speech
from test_notes import notes, correction
from test_note_edits import generated, command
from test_lifecycle import remove
from notetaker import models as m, question_worker as worker
from notetaker.question_contract import validate_questions
from notetaker.lifecycle import reconcile_deletion
from notetaker.resource_budget import available, inference_slot


class FakeQuestions:
    def __init__(self, after=None, bad=False): self.after, self.bad = after, bad
    def generate_questions(self, evidence, pref, preview):
        preview('What condition is required?')
        if self.after: self.after()
        source = evidence['sources'][0]
        return [{'id': 'q1', 'kind': 'practice', 'objective': 'conditions',
            'question': 'What condition does binary search require?', 'answer': source['text'],
            'citations': [{'source_id': 'foreign' if self.bad else source['id'], 'quote': source['text']}]}], {
                'model': pref.model, 'model_digest': pref.model_digest, 'semantic_support': 'not_evaluated'}


def post(client, headers, path, body, key=None):
    return client.post(path, json=body, headers={**headers, 'idempotency-key': key or str(uuid4())})


def enqueue(client, headers, path, **changes):
    state = client.get(path + '/study/questions').json()
    body = {'revision_id': state['revision_id'], 'block_id': state['blocks'][0]['id'],
        'preference_id': state['preference_id'], 'kind': 'mixed', 'count': 4, **changes}
    return post(client, headers, path + '/study/questions', body)


def ready(notes):
    app, client, headers, path, _ = notes
    generated(app, client, path)
    queued = enqueue(client, headers, path)
    assert queued.status_code == 202, queued.text
    selected = worker.claim(app.state.sessions)
    assert selected and worker.execute(app.state.sessions, FakeQuestions(), selected, heartbeat=False)
    return path + '/study/questions/' + queued.json()['id']


def test_generation_is_pinned_idempotent_and_owned(notes):
    app, client, headers, path, _ = notes
    generated(app, client, path)
    state = client.get(path + '/study/questions').json()
    body = {'revision_id': state['revision_id'], 'block_id': state['blocks'][0]['id'], 'preference_id': state['preference_id']}
    key = str(uuid4())
    assert client.post(path + '/study/questions', json=body).status_code == 403
    first = post(client, headers, path + '/study/questions', body, key)
    assert first.status_code == 202, first.text
    assert post(client, headers, path + '/study/questions', body, key).json()['id'] == first.json()['id']
    assert post(client, headers, path + '/study/questions', {**body, 'count': 2}, key).status_code == 409
    assert enqueue(client, headers, path).status_code == 409
    endpoint = path + '/study/questions/' + first.json()['id']
    selected = worker.claim(app.state.sessions)
    with app.state.sessions() as db:
        assert not available(db, 'notes.generate')
    with inference_slot(app.state.sessions, 'notes.generate') as acquired:
        assert acquired
        with inference_slot(app.state.sessions, 'notes.generate') as second:
            assert not second
    assert worker.execute(app.state.sessions, FakeQuestions(), selected, heartbeat=False)
    saved = client.get(endpoint).json()
    assert saved['status'] == 'completed' and saved['questions'][0]['citations'] and not saved['stale']
    assert saved['questions'][0]['quality']['support'] == -1
    other = lecture(client, headers, course(client, headers)['id'])
    assert client.get('/lectures/' + other['id'] + '/study/questions/' + saved['id']).status_code == 404
    assert enqueue(client, headers, path, block_id='foreign').status_code == 409
    assert enqueue(client, headers, path, count=9).status_code == 422
    client.cookies.clear()
    assert client.get(endpoint).status_code == 401


@pytest.mark.parametrize('change', ['correction', 'edit', 'model', 'settings', 'audio', 'lifecycle', 'delete', 'cancel'])
def test_generation_fences_changed_inputs_and_preserves_previous_set(notes, change):
    app, client, headers, path, _ = notes
    previous = ready(notes)
    saved = client.get(previous).json()['questions']
    request = enqueue(client, headers, path).json()
    chosen = worker.claim(app.state.sessions)
    def alter():
        if change == 'correction': correction(client, headers, path)
        elif change == 'edit':
            base = client.get(path + '/notes').json()['revision']
            passage = base['content']['blocks'][0]['passages'][0]
            assert command(client, headers, path, {'action': 'save', 'expected_version': 0,
                'base_id': base['id'], 'passages': [{'id': passage['id'], 'text': 'Updated by student.'}]}).status_code == 200
        elif change == 'cancel':
            assert post(client, headers, path + '/study/questions/' + request['id'] + '/cancel', {}).status_code == 200
        else:
            with app.state.sessions() as db:
                lecture_row = db.get(m.Lecture, path.split('/')[-1])
                if change == 'delete': lecture_row.tombstoned = True
                elif change == 'audio': lecture_row.audio_epoch += 1
                elif change == 'lifecycle': lecture_row.lifecycle_epoch += 1
                elif change == 'model':
                    old = db.scalar(select(m.NotePreference).where(m.NotePreference.lecture_id == lecture_row.id))
                    db.add(m.NotePreference(lecture_id=lecture_row.id, version=2, model=old.model, model_digest=old.model_digest, enabled=False))
                else:
                    old = db.scalar(select(m.SettingsVersion).where(m.SettingsVersion.lecture_id == lecture_row.id))
                    db.add(m.SettingsVersion(lecture_id=lecture_row.id, version=2, depth=old.depth, format=old.format))
                db.commit()
    assert not worker.execute(app.state.sessions, FakeQuestions(after=alter), chosen, heartbeat=False)
    with app.state.sessions() as db:
        assert db.get(m.QuestionSet, request['id']).content is None
        assert db.get(m.QuestionSet, previous.split('/')[-1]).content[0]['question'] == saved[0]['question']


def test_invalid_generation_reclaim_and_cancel_are_fenced(notes):
    app, client, headers, path, _ = notes
    ready(notes)
    queued = enqueue(client, headers, path).json()
    chosen = worker.claim(app.state.sessions)
    with app.state.sessions() as db:
        db.get(m.Job, chosen[0]).lease_expires_at = m.now() - timedelta(seconds=1); db.commit()
    reclaimed = worker.claim(app.state.sessions)
    assert reclaimed[1] != chosen[1] and not worker.renew(app.state.sessions, *chosen)
    assert not worker.execute(app.state.sessions, FakeQuestions(), chosen, heartbeat=False)
    assert not worker.execute(app.state.sessions, FakeQuestions(bad=True), reclaimed, heartbeat=False)
    assert client.get(path + '/study/questions/' + queued['id']).json()['error_code'] == 'invalid_output'
    assert client.get(path + '/study/questions').json()['sets'][1]['status'] == 'completed'


def test_edits_quality_history_assessment_conflicts_and_deletion(notes):
    app, client, headers, path, _ = notes
    endpoint = ready(notes)
    original = client.get(endpoint).json()['questions'][0]
    cardpath = endpoint + '/q1'
    assess = {'question_revision': original['revision_id'], 'expected_version': 0, 'rating': 'confident'}
    assert post(client, headers, cardpath + '/reviews', assess).status_code == 200
    edit = {'expected_version': 0, 'question': 'What prerequisite is necessary for binary search?', 'answer': original['answer'],
        'quality': {'support': 2, 'answerability': 2, 'clarity': 1, 'usefulness': 2}, 'feedback': 'Clarify what counts as sorted.'}
    key = str(uuid4())
    first = post(client, headers, cardpath + '/edits', edit, key)
    assert first.status_code == 200, first.text
    assert first.json()['student_edited'] and first.json()['review']['rating'] == 'unreviewed'
    assert post(client, headers, cardpath + '/edits', edit, key).json()['revision_id'] == first.json()['revision_id']
    assert post(client, headers, cardpath + '/edits', edit).status_code == 409
    assert post(client, headers, cardpath + '/reviews', assess).status_code == 409
    assess['question_revision'] = first.json()['revision_id']
    assert post(client, headers, cardpath + '/reviews', assess).status_code == 422
    restored = post(client, headers, cardpath + '/edits', {**edit, 'expected_version': 1,
        'question': original['question'], 'quality': dict.fromkeys(edit['quality'], 2)})
    assert restored.status_code == 200
    assess['question_revision'] = restored.json()['revision_id']
    assert post(client, headers, cardpath + '/reviews', assess).status_code == 200
    versions = client.get(cardpath + '/history').json()
    assert [v['version'] for v in versions] == [2, 1, 0]
    assert versions[-1]['question'] == original['question']
    assert client.get(endpoint).json()['quality_counts'] == {'reviewed': 1, 'needs_work': 0, 'total': 1}
    correction(client, headers, path)
    assert client.get(endpoint).json()['stale']
    assert post(client, headers, cardpath + '/reviews', {**assess, 'expected_version': 1}).status_code == 409
    deletion = remove(client, headers, path).json()
    reconcile_deletion(app.state.sessions, app.state.audio_store, deletion['id'])
    assert post(client, headers, cardpath + '/edits', edit, key).status_code == 404
    with app.state.sessions() as db:
        for table in (m.QuestionSet, m.QuestionEdit, m.LearningReview):
            assert db.scalar(select(func.count()).select_from(table)) == 0


def test_cloud_generation_requires_additional_consent(notes):
    app, client, headers, path, _ = notes
    generated(app, client, path)
    with app.state.sessions() as db:
        db.add(m.NotePreference(lecture_id=path.split('/')[-1], version=2, model='openai/example', model_digest='c'*64, enabled=True)); db.commit()
    assert enqueue(client, headers, path).status_code == 422
    assert enqueue(client, headers, path, cloud_consent=True).status_code == 202


@pytest.mark.parametrize('fault', ['foreign', 'quote', 'duplicate', 'blank', 'count', 'kind', 'extra', 'invented_number'])
def test_question_contract_rejects_structural_failures(fault):
    evidence = {'sources': [{'id': 's1', 'text': 'Binary search requires sorted input.'}], 'count': 2, 'kind': 'practice'}
    question = {'kind': 'practice', 'objective': 'conditions', 'question': 'What does binary search require?',
        'answer': 'Binary search requires sorted input.', 'citations': [{'source_id': 's1', 'quote': 'requires sorted input'}]}
    output = {'questions': [deepcopy(question)]}
    if fault == 'foreign': output['questions'][0]['citations'][0]['source_id'] = 'foreign'
    elif fault == 'quote': output['questions'][0]['citations'][0]['quote'] = 'requires unsorted input'
    elif fault == 'duplicate': output['questions'].append(deepcopy(question))
    elif fault == 'blank': output['questions'][0]['answer'] = ' ' * 8
    elif fault == 'count': evidence['count'] = 0
    elif fault == 'kind': output['questions'][0]['kind'] = 'flashcard'
    elif fault == 'invented_number': output['questions'][0]['question'] = 'How does binary search handle 1024 unsorted items?'
    else: output['questions'][0]['approved'] = True
    with pytest.raises(ValueError): validate_questions(output, evidence)


def test_question_adapter_routes_and_rechecks_local_identity():
    from notetaker.question_provider import generate_questions
    evidence = {'sources': [{'id': 's1', 'text': 'Binary search requires sorted input.'}], 'count': 1, 'kind': 'practice'}
    output = {'questions': [{'kind': 'practice', 'objective': 'conditions', 'question': 'What does binary search require?',
        'answer': evidence['sources'][0]['text'], 'citations': [{'source_id': 's1', 'quote': 'sorted input'}]}]}
    calls = []
    class Local:
        def verify(self, model, expected): calls.append('verify'); return {'digest': expected}, {}
        def request(self, route, body, timeout):
            calls.append(body)
            return {'prompt_eval_count': 200} if body['options']['num_predict'] == 1 else {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(output)}}
    generated_questions, metadata = generate_questions(Local(), evidence, SimpleNamespace(model='qwen3:4b', model_digest='d'*64))
    assert generated_questions[0]['id'] == 'q1' and metadata['semantic_support'] == 'not_evaluated'
    assert calls.count('verify') == 3
    assert calls[1]['messages'][0]['content'].startswith('Create a small study set')
    assert '$ref' not in json.dumps(calls[1]['format']) and 'maxLength' not in json.dumps(calls[1]['format'])


@pytest.mark.parametrize('model', ['openai/example', 'anthropic/example', 'chatgpt/example', 'claude-subscription/example'])
def test_question_adapter_uses_selected_bridge_without_fallback(model):
    from notetaker.question_provider import generate_questions
    from notetaker.note_provider import NoteFailure
    evidence = {'sources': [{'id': 's1', 'text': 'An enzyme lowers activation energy.'}], 'count': 1, 'kind': 'flashcard'}
    output = {'questions': [{'kind': 'flashcard', 'objective': 'definition', 'question': 'What does an enzyme lower?',
        'answer': evidence['sources'][0]['text'], 'citations': [{'source_id': 's1', 'quote': 'lowers activation energy'}]}]}
    calls = []
    class Provider:
        def verify(self, name, expected):
            assert name == model
            calls.append('verify')
            return {'digest': expected}, {}
        @property
        def bridge(self): return self
        def generate(self, name, expected, messages, preview):
            assert name == model and 'OUTPUT_SCHEMA' in messages[0]['content']
            calls.append('bridge'); return json.dumps(output), {}
    pref = SimpleNamespace(model=model, model_digest='d'*64)
    adapter = Provider()
    assert generate_questions(adapter, evidence, pref)[1]['processing_location'] == 'cloud'
    assert calls == ['verify', 'bridge', 'verify']
    def broken(*args): raise NoteFailure('provider_authentication')
    adapter.generate = broken
    with pytest.raises(NoteFailure) as failed: generate_questions(adapter, evidence, pref)
    assert failed.value.code == 'provider_authentication'


def test_evaluation_separates_citation_validity_from_answer_quality():
    from notetaker.question_evaluation import diagnostics, evidence_for
    from notetaker.note_contract import ROOT
    cases = json.loads((ROOT / 'evaluations/fixtures/questions-v1.json').read_text())['cases']
    for case in cases:
        evidence = evidence_for(case)
        question = {'kind': 'practice', 'objective': 'explanation', 'question': 'What does this evidence establish?',
            'answer': 'This answer is unrelated to the actual evidence.',
            'citations': [{'source_id': evidence['sources'][0]['id'], 'quote': case['text']}]}
        # A real source quote is not proof that the answer is semantically supported.
        canonical = validate_questions({'questions': [question]}, evidence)
        assert not diagnostics(case, canonical)['fixture_signals_pass']
        question['answer'] = case['text']
        assert diagnostics(case, [question])['fixture_signals_pass']
