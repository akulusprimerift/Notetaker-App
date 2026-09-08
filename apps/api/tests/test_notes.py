import copy
import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from test_workspace import setup
from test_capture import capture
from test_transcription import speech, finish_all
from notetaker.models import Job, Lecture, NoteRevision, NoteRequest, NotePreference, now
from notetaker.note_contract import validate_notes
from notetaker.note_provider import NoteFailure, OllamaNotes, CONTEXT
from notetaker.note_worker import plan, claim, execute, publish, renew
from notetaker.notes import inputs
from notetaker.config import Settings
from notetaker.note_draft import prepare, canonical

DIGEST = 'a' * 64


def valid(evidence):
    return {'schema_version': 1, 'source_snapshot_id': evidence['source_snapshot_id'], 'settings_version': evidence['settings_version'],
        'blocks': [{'id': 'b', 'topic': 'Binary search', 'kind': 'definition',
            'passages': [{'id': str(i), 'text': s['text'], 'evidence_kind': 'exact_quote',
                'sources': [{'source_id': s['id'], 'quote': s['text'], 'occurrence': 0}]} for i,s in enumerate(evidence['sources'])]}],
        'issues': [], 'coverage': [{'source_id': s['id'], 'disposition': 'used', 'reason': 'Definition retained.'} for s in evidence['sources']]}


class FakeNotes:
    def __init__(self, after=None, corrupt=False, failure=None): self.after, self.corrupt, self.failure = after, corrupt, failure
    def models(self): return [{'name': 'qwen3:4b', 'digest': DIGEST, 'size': 10000000}]
    def verify(self, model):
        if model != 'qwen3:4b': raise NoteFailure('model_unavailable')
        return self.models()[0], {}
    def generate(self, evidence, pref):
        if self.after: self.after()
        if self.failure: raise NoteFailure(self.failure)
        output = valid(evidence)
        if self.corrupt: output['blocks'][0]['passages'][0]['sources'][0]['source_id'] = 'other-lecture'
        return output, {'model': pref.model, 'model_digest': pref.model_digest, 'provider': 'synthetic-test-double'}


@pytest.fixture
def notes(speech):
    app, client, headers, path, run = speech
    finish_all(app)
    app.state.note_provider = FakeNotes()
    response = client.post(path + '/notes/model', headers={**headers, 'idempotency-key': str(uuid4())},
        json={'expected_version': 0, 'model': 'qwen3:4b', 'enabled': True})
    assert response.status_code == 200, response.text
    return speech


def correction(client, headers, path, text='Binary search only works on a sorted array.'):
    segment = client.get(path + '/transcript').json()['snapshot']['segments'][0]
    response = client.post(path + '/transcript/segments/' + segment['segment_id'] + '/corrections',
        headers={**headers, 'idempotency-key': str(uuid4())}, json={'expected_version': segment['id'], 'text': text})
    assert response.status_code == 200


def test_selected_model_automatically_writes_saved_notes(notes):
    app, client, _, path, _ = notes
    assert client.get(path + '/notes').json()['status'] == 'queued'
    plan(app.state.sessions)
    with app.state.sessions() as db: assert db.scalar(select(func.count()).select_from(NoteRequest)) == 1
    chosen = claim(app.state.sessions)
    assert chosen and execute(app.state.sessions, FakeNotes(), chosen, heartbeat=False)
    data = client.get(path + '/notes').json()
    assert data['status'] == 'ready' and data['revision']['revision'] == 1 and not data['stale']
    assert len(data['revision']['resolved_citations']) == 2
    assert claim(app.state.sessions) is None
    assert client.get(path + '/snapshot').json()['notes']['revision']['id'] == data['revision']['id']


def test_corrected_transcript_refreshes_notes_and_keeps_old_export(notes):
    app, client, headers, path, _ = notes
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    old = client.get(path + '/notes').json()['revision']
    old_export = client.get(path + '/notes/revisions/' + old['id'] + '/export').text
    correction(client, headers, path)
    assert client.get(path + '/notes').json()['stale']
    plan(app.state.sessions)
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    data = client.get(path + '/notes').json()
    assert data['revision']['revision'] == 2 and not data['stale']
    assert 'only works' in json.dumps(data['revision']['content'])
    assert client.get(path + '/notes/revisions/' + old['id'] + '/export').text == old_export


@pytest.mark.parametrize('change', ['correction', 'audio_epoch', 'lifecycle', 'delete', 'model', 'pause'])
def test_changed_input_cannot_publish(notes, change):
    app, client, headers, path, _ = notes
    def after():
        if change == 'correction': correction(client, headers, path)
        elif change in ('model', 'pause'):
            r = client.post(path + '/notes/model', headers={**headers, 'idempotency-key': str(uuid4())},
                json={'expected_version': 1, 'model': 'qwen3:4b', 'enabled': change != 'pause'})
            assert r.status_code == 200
        else:
            with app.state.sessions() as db:
                lecture = db.get(Lecture, path.split('/')[-1])
                if change == 'delete': lecture.tombstoned = True
                elif change == 'audio_epoch': lecture.audio_epoch += 1
                else: lecture.lifecycle_epoch += 1
                db.commit()
    assert not execute(app.state.sessions, FakeNotes(after=after), claim(app.state.sessions), heartbeat=False)
    with app.state.sessions() as db: assert db.scalar(select(func.count()).select_from(NoteRevision)) == 0


def test_concurrent_claims_and_expired_attempt_fence(notes):
    app, *_ = notes
    with ThreadPoolExecutor(max_workers=2) as pool: claims = list(pool.map(lambda _: claim(app.state.sessions), range(2)))
    old = next(c for c in claims if c)
    assert sum(c is not None for c in claims) == 1
    assert renew(app.state.sessions, *old)
    with app.state.sessions() as db:
        db.get(Job, old[0]).lease_expires_at = now() - timedelta(seconds=1); db.commit()
    new = claim(app.state.sessions)
    assert new[1] != old[1]
    assert not execute(app.state.sessions, FakeNotes(), old, heartbeat=False)
    assert execute(app.state.sessions, FakeNotes(), new, heartbeat=False)
    assert not execute(app.state.sessions, FakeNotes(), new, heartbeat=False)


def test_invalid_output_preserves_last_revision_and_retry_is_idempotent(notes):
    app, client, headers, path, _ = notes
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    old = client.get(path + '/notes').json()['revision']['id']
    correction(client, headers, path); plan(app.state.sessions)
    assert not execute(app.state.sessions, FakeNotes(corrupt=True), claim(app.state.sessions), heartbeat=False)
    data = client.get(path + '/notes').json()
    assert data['error_code'] == 'invalid_output' and data['revision']['id'] == old and data['stale']
    h = {**headers, 'idempotency-key': str(uuid4())}
    assert client.post(path + '/notes/retry', headers=h).status_code == 200
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    assert client.post(path + '/notes/retry', headers=h).status_code == 200
    assert claim(app.state.sessions) is None


def test_model_unavailable_bounded_retry_keeps_transcript(notes):
    app, client, _, path, _ = notes
    before = client.get(path + '/transcript').json()['snapshot']
    for attempt in range(3):
        chosen = claim(app.state.sessions)
        assert chosen and not execute(app.state.sessions, FakeNotes(failure='model_unavailable'), chosen, heartbeat=False)
        with app.state.sessions() as db:
            job = db.get(Job, chosen[0]); job.due_at = now(); db.commit()
    assert client.get(path + '/notes').json()['status'] == 'needs_attention'
    assert claim(app.state.sessions) is None
    assert client.get(path + '/transcript').json()['snapshot'] == before


def test_model_conflict_csrf_idempotency_and_private_export(notes):
    app, client, headers, path, _ = notes
    body = {'model': 'qwen3:4b', 'expected_version': 1, 'enabled': True}
    h = {**headers, 'idempotency-key': str(uuid4())}
    assert client.post(path + '/notes/model', json=body).status_code == 403
    assert client.post(path + '/notes/model', headers=h, json=body).status_code == 200
    def unavailable(*args): raise NoteFailure('model_unavailable')
    app.state.note_provider.verify = unavailable
    assert client.post(path + '/notes/model', headers=h, json=body).json()['version'] == 2
    assert client.post(path + '/notes/model', headers={**h,'idempotency-key':str(uuid4())}, json=body).status_code == 409
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    revision = client.get(path + '/notes').json()['revision']['id']
    export_path = path + '/notes/revisions/' + revision + '/export'
    exported = client.get(export_path)
    assert 'Source appendix' in exported.text and 'Binary search' in exported.text
    assert exported.headers['content-disposition'].endswith('.md"')
    assert client.get('/lectures/' + str(uuid4()) + '/notes/revisions/' + revision + '/export').status_code == 404
    client.cookies.clear()
    for route in (export_path, path+'/notes', '/note-models'):
        assert client.get(route).status_code == 401


@pytest.mark.parametrize('corrupt', ['cross_source','quote','occurrence','missing_coverage','duplicate','ai','exact','unknown_field','empty','metadata'])
def test_contract_rejects_invalid_or_unsupported_notes(corrupt):
    evidence = {'source_snapshot_id':'snap','settings_version':1,'allow_ai_explanations':False,'sources':[{'id':'s','text':'😀 sorted array'}]}
    output = valid(evidence)
    passage = output['blocks'][0]['passages'][0]
    if corrupt == 'cross_source': passage['sources'][0]['source_id'] = 'other'
    if corrupt == 'quote': passage['sources'][0]['quote'] = 'unsorted array'
    if corrupt == 'occurrence': passage['sources'][0]['occurrence'] = 2**63
    if corrupt == 'missing_coverage': output['coverage'] = []
    if corrupt == 'duplicate': output['blocks'].append(copy.deepcopy(output['blocks'][0]))
    if corrupt == 'ai': passage['evidence_kind'] = 'ai_explanation'
    if corrupt == 'exact': passage['text'] = 'changed'
    if corrupt == 'unknown_field': output['arbitrary'] = True
    if corrupt == 'empty': passage['text'] = '  '
    if corrupt == 'metadata': output['settings_version'] = 2
    with pytest.raises(Exception): validate_notes(output, evidence)


def test_unicode_offsets_and_safe_export(notes):
    app, client, headers, path, _ = notes
    correction(client, headers, path, '😀 sorted <script>alert(1)</script> [click](javascript:alert(1)) ```')
    plan(app.state.sessions)
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    revision = client.get(path+'/notes').json()['revision']
    c = revision['resolved_citations'][0]
    text = revision['content']['blocks'][0]['passages'][0]['text']
    assert c['end'] == len(text)
    exported = client.get(path+'/notes/revisions/'+revision['id']+'/export').text
    assert '<script>' not in exported and '[click](javascript:' not in exported and '```' not in exported


def test_app_owns_citations_ids_and_coverage_without_model_bookkeeping():
    evidence={'source_snapshot_id':'snap','settings_version':1,'allow_ai_explanations':False,
        'sources':[{'id':str(uuid4()),'text':'The slide is not visible.'},{'id':str(uuid4()),'text':'An unused aside.'}]}
    request, citations = prepare(evidence)
    draft={'blocks':[{'topic':'Missing visual','kind':'uncertainty','passages':[{'text':'The slide is unavailable.','source_ids':['s1']}]}],
        'issues':[{'code':'missing_visual','detail':'Slide unavailable.','source_ids':['s1']}]}
    output=canonical(draft,evidence,citations)
    assert output['coverage'][0]['disposition']=='used'
    assert output['coverage'][1]['disposition']=='omitted'
    assert output['blocks'][0]['passages'][0]['sources'][0]['quote']=='The slide is not visible.'
    assert validate_notes(output,evidence)[0]['source_id']==evidence['sources'][0]['id']
    draft['blocks'][0]['passages'][0]['source_ids']=['s99']
    with pytest.raises(ValueError,match='unknown_source'):canonical(draft,evidence,citations)


def test_long_unicode_transcript_sources_have_exact_resolvable_spans():
    evidence={'source_snapshot_id':'snap','settings_version':1,'allow_ai_explanations':False,
        'sources':[{'id':'original','text':'😀 repetition '*800}]}
    request,citations=prepare(evidence)
    assert ''.join(s['text'] for s in request['sources'])==evidence['sources'][0]['text']
    assert all(len(c['quote'])<=3000 for c in citations.values())
    draft={'blocks':[{'topic':'Repeated material','kind':'explanation','passages':[
        {'text':'Repeated material.', 'source_ids':[s['id']]} for s in request['sources']]}], 'issues':[]}
    assert len(validate_notes(canonical(draft,evidence,citations),evidence))==len(request['sources'])


def test_provider_excludes_remote_aliases_and_unknown_tokenizers():
    provider = OllamaNotes(Settings(preview=True,database_url='sqlite://'))
    base = {'name':'qwen3:4b','digest':DIGEST,'size':10000000,'details':{'format':'gguf','family':'qwen3'}}
    provider.request = lambda *args,**kwargs: {'models':[base,{**base,'name':'remote','remote_host':'https://ollama.com'},
        {**base,'name':'other','details':{'format':'gguf','family':'unknown'}},{**base,'name':'tiny','size':200}]}
    assert [m['name'] for m in provider.models()] == ['qwen3:4b']
    with pytest.raises(ValueError): Settings(ollama_url='https://ollama.com')


def test_context_limit_rejects_whole_input_before_inference():
    provider = OllamaNotes(Settings())
    provider.verify = lambda *args: ({'digest': DIGEST},{'template':''})
    provider.request = lambda *args,**kwargs: pytest.fail('Oversized content must not be sent')
    evidence={'source_snapshot_id':'s','settings_version':1,'allow_ai_explanations':False,'sources':[{'id':'s','text':'x'*CONTEXT}]}
    with pytest.raises(NoteFailure) as failure:
        provider.generate(evidence, SimpleNamespace(model='qwen3:4b', model_digest=DIGEST))
    assert failure.value.code == 'context_limit'


@pytest.mark.parametrize('mode', ['truncated', 'tools', 'changed', 'preflight'])
def test_provider_rejects_incomplete_tool_output_or_changed_model(mode):
    provider = OllamaNotes(Settings())
    checks = []
    def verify(*args):
        checks.append(1)
        if mode == 'changed' and len(checks) == 3: raise NoteFailure('model_changed')
        return {'digest': DIGEST}, {'template': ''}
    provider.verify = verify
    evidence = {'source_snapshot_id':'s','settings_version':1,'allow_ai_explanations':False,'sources':[{'id':'s','text':'Sorted array.'}]}
    calls = []
    def request(route, body=None, **kwargs):
        calls.append(body)
        if len(calls) == 1: return {'prompt_eval_count': CONTEXT if mode == 'preflight' else 2000}
        return {'done': True, 'done_reason': 'length' if mode == 'truncated' else 'stop',
            'message': {'content':json.dumps(valid(evidence)), 'tool_calls':[{'name':'untrusted'}] if mode == 'tools' else []}}
    provider.request = request
    with pytest.raises(NoteFailure) as failure:
        provider.generate(evidence, SimpleNamespace(model='qwen3:4b',model_digest=DIGEST))
    assert failure.value.code == {'truncated':'truncated_output','tools':'invalid_output','changed':'model_changed','preflight':'context_limit'}[mode]
    assert calls[0]['options']['num_predict'] == 1


def test_course_neutral_preferences_are_versioned_and_drive_generation(notes):
    app,client,headers,path,_=notes
    body={'expected_version':1,'model':'qwen3:4b','enabled':True,'depth':'brief','format':'question_answer',
        'instructions':'Use plain language and explain historical causes.'}
    response=client.post(path+'/notes/model',headers={**headers,'idempotency-key':str(uuid4())},json=body)
    assert response.status_code==200
    data=client.get(path+'/notes').json()
    assert data['profile']=={k:body[k] for k in ('depth','format','instructions')}
    snapshot=client.get(path+'/snapshot').json()
    assert snapshot['settings']['depth']=='brief' and snapshot['settings']['version']==2
    chosen=claim(app.state.sessions)
    with app.state.sessions() as db:
        evidence=inputs(db,db.get(NoteRequest,db.get(Job,chosen[0]).input_revision))
    assert evidence['profile']==data['profile'] and evidence['settings_version']==2
    assert execute(app.state.sessions,FakeNotes(),chosen,heartbeat=False)
    assert client.get(path+'/notes').json()['status']=='ready'
