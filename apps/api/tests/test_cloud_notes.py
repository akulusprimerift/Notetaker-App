import copy
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import httpx
import pytest
from test_workspace import setup
from test_capture import capture
from test_transcription import speech
from test_notes import notes
from notetaker.cloud_notes import NoteProviders
from notetaker.note_provider import NoteFailure
from notetaker.provider_connections import Connections
from notetaker.subscription_notes import client_environment, codex_args, claude_args

EVIDENCE = {'source_snapshot_id':'sample', 'settings_version':1, 'allow_ai_explanations':False,
    'sources':[{'id':'water', 'text':'Cooling water vapor condenses into liquid water.'}]}
DRAFT = {'blocks':[{'topic':'Condensation', 'kind':'explanation',
    'passages':[{'text':'Cooling vapor produces liquid water.', 'source_ids':['s1']}]}], 'issues':[]}


@pytest.mark.parametrize('provider', ['openai', 'anthropic'])
def test_cloud_stream_validation_and_no_secret_history(tmp_path, provider):
    store = Connections(tmp_path)
    store.save(provider, 'test-model', api_key='test-secret-only')
    assert b'test-secret-only' not in store.path(provider).read_bytes()
    row = store.read(provider)
    pref = SimpleNamespace(model=provider+'/test-model', model_digest=row['id'])
    raw = json.dumps(DRAFT); sent = []
    def transport(request):
        sent.append(request)
        body = json.loads(request.content)
        assert body['model'] == 'test-model' and body['stream'] is True
        if provider == 'openai':
            assert request.headers['authorization'] == 'Bearer test-secret-only'
            events = [{'choices':[{'delta':{'content':raw[:80]},'finish_reason':None}]},
                {'choices':[{'delta':{'content':raw[80:]},'finish_reason':'stop'}]}]
        else:
            assert request.headers['x-api-key'] == 'test-secret-only'
            events = [{'type':'content_block_delta','delta':{'text':raw[:80]}},
                {'type':'content_block_delta','delta':{'text':raw[80:]}},
                {'type':'message_delta','delta':{'stop_reason':'end_turn'},'usage':{'output_tokens':90}}]
        return httpx.Response(200, content=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
    adapter = NoteProviders(SimpleNamespace(standalone=True, provider_directory=str(tmp_path),
        ollama_url='http://127.0.0.1:11434'), transport=httpx.MockTransport(transport))
    previews = []
    content, metadata = adapter.generate_stream(EVIDENCE, pref, previews.append)
    assert content['blocks'][0]['passages'][0]['sources'][0]['source_id'] == 'water'
    assert 'Cooling vapor' in previews[-1] and len(sent) == 1
    assert 'test-secret' not in json.dumps(metadata)
    store.remove(provider)
    with pytest.raises(NoteFailure) as failure: adapter.generate(EVIDENCE, pref)
    assert failure.value.code == 'connection_unavailable' and len(sent) == 1


@pytest.mark.parametrize('status,code', [(401,'provider_authentication'), (429,'provider_limit'), (302,'model_unavailable')])
def test_cloud_errors_never_redirect_or_fallback(tmp_path, status, code):
    store = Connections(tmp_path); store.save('openai','test-model',api_key='secret')
    calls = []
    def transport(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={'location':'https://other.invalid'}, text='secret provider detail')
    adapter = NoteProviders(SimpleNamespace(standalone=True, provider_directory=str(tmp_path), ollama_url='http://127.0.0.1:1'),
        transport=httpx.MockTransport(transport))
    pref = SimpleNamespace(model='openai/test-model', model_digest=store.read('openai')['id'])
    with pytest.raises(NoteFailure) as failure: adapter.generate(EVIDENCE, pref)
    assert failure.value.code == code and len(calls) == 1


def test_cloud_choice_requires_lecture_consent(notes, tmp_path):
    app, client, headers, path, _ = notes
    store = Connections(tmp_path); store.save('openai','test-model',api_key='secret')
    app.state.note_provider = NoteProviders(SimpleNamespace(standalone=True, provider_directory=str(tmp_path), ollama_url='http://127.0.0.1:1'))
    body = {'model':'openai/test-model', 'expected_version':1, 'enabled':True}
    def post(value): return client.post(path+'/notes/model', json=value, headers={**headers,'idempotency-key':str(uuid4())})
    assert post(body).status_code == 422
    accepted = post({**body,'cloud_consent':True})
    assert accepted.status_code == 200 and accepted.json()['model'] == 'openai/test-model'
    assert 'secret' not in json.dumps(client.get(path+'/notes').json())


def test_subscription_commands_isolate_credentials_and_tools(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','do-not-inherit')
    monkeypatch.setenv('ANTHROPIC_BASE_URL','https://other.invalid')
    monkeypatch.setenv('CLAUDE_CODE_OAUTH_TOKEN','do-not-copy')
    for provider in ('chatgpt','claude-subscription'):
        env = client_environment(provider,tmp_path)
        assert 'OPENAI_API_KEY' not in env and 'ANTHROPIC_BASE_URL' not in env and 'CLAUDE_CODE_OAUTH_TOKEN' not in env
    args = codex_args('codex.exe')
    assert 'features.shell_tool=false' in args and 'web_search="disabled"' in args
    args = claude_args('claude.exe','sonnet')
    assert args[args.index('--tools')+1] == '' and '--no-session-persistence' in args


@pytest.mark.parametrize('provider', ['chatgpt', 'claude-subscription'])
def test_subscription_routes_through_selected_bridge_and_revalidates(tmp_path, monkeypatch, provider):
    from notetaker import subscription_notes
    executable = tmp_path/'official.exe'; executable.write_bytes(b'test fixture, never executed')
    store = Connections(tmp_path); store.save(provider,'test-model',executable=str(executable))
    pref = SimpleNamespace(model=provider+'/test-model', model_digest=store.read(provider)['id'])
    calls = []
    def generate(selected, row, messages, directory, preview):
        calls.append(selected); preview('Streaming sample')
        return json.dumps(DRAFT), {'billing':'subscription'}
    monkeypatch.setattr(subscription_notes, 'subscription_generate', generate)
    adapter = NoteProviders(SimpleNamespace(standalone=True, provider_directory=str(tmp_path), ollama_url='http://127.0.0.1:1'))
    previews = []
    output, metadata = adapter.generate(EVIDENCE,pref,previews.append)
    assert calls == [provider] and previews == ['Streaming sample']
    assert metadata['provider'] == provider and output['blocks']
    store.save(provider,'test-model',executable=str(executable))
    with pytest.raises(NoteFailure): adapter.generate(EVIDENCE,pref)
    assert calls == [provider]
