import io
import json
from types import SimpleNamespace
import pytest
from notetaker import subscription_notes as bridge
from notetaker.note_provider import NoteFailure


def test_codex_auth_gate_and_incremental_events(tmp_path, monkeypatch):
    raw = json.dumps({'blocks':[{'topic':'Water', 'text':'Condensation'}]})
    events = [{'id':1,'result':{}}, {'id':2,'result':{'account':{'type':'chatgpt'}}},
        {'id':3,'result':{'thread':{'id':'isolated'}}}, {'id':4,'result':{}},
        {'method':'item/agentMessage/delta','params':{'delta':raw[:30]}},
        {'method':'item/agentMessage/delta','params':{'delta':raw[30:]}},
        {'method':'item/completed','params':{'item':{'type':'agentMessage','text':raw}}},
        {'method':'turn/completed','params':{'turn':{'status':'completed'}}}]
    instances = []
    class Client:
        def __init__(self, *args): self.sent=[]; self.closed=False; instances.append(self)
        def send(self, event): self.sent.append(event)
        def event(self): return events.pop(0)
        def close(self): self.closed=True
    monkeypatch.setattr(bridge,'ClientProcess',Client)
    previews=[]
    result, _ = bridge.codex_generate({'executable':'unused','model':'selected-model'},
        [{'role':'user','content':'Synthetic evidence'}],tmp_path,previews.append)
    assert result == raw and previews[-1] == 'Water\n\nCondensation'
    sent = instances[0].sent
    assert sent[-2]['params']['ephemeral'] is True
    assert sent[-2]['params']['sandbox'] == 'read-only'
    assert sent[-1]['params']['input'][0]['text'] == 'Synthetic evidence'
    assert instances[0].closed
    events[:] = [{'id':1,'result':{}}, {'id':2,'result':{'account':{'type':'apiKey'}}}]
    with pytest.raises(NoteFailure) as error:
        bridge.codex_generate({'executable':'unused','model':'selected-model'},[],tmp_path,None)
    assert error.value.code == 'provider_authentication'
    assert not any(e.get('method') == 'turn/start' for e in instances[-1].sent)


def test_claude_subscription_gate_and_stream(tmp_path, monkeypatch):
    auth = {'authMethod':'claude.ai'}
    monkeypatch.setattr(bridge.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=json.dumps(auth).encode()))
    events = [{'type':'stream_event','event':{'delta':{'text':'{"topic":"Water"}'}}},
        {'type':'result','subtype':'success','is_error':False,'result':'{"topic":"Water"}'}]
    instances=[]
    class Client:
        def __init__(self,*args):
            self.process=SimpleNamespace(stdin=io.BytesIO()); self.closed=False; instances.append(self)
        def event(self): return events.pop(0)
        def close(self): self.closed=True
    monkeypatch.setattr(bridge,'ClientProcess',Client)
    previews=[]
    result,_=bridge.claude_generate({'executable':'unused','model':'selected'},[],tmp_path,previews.append)
    assert result == '{"topic":"Water"}' and previews == ['Water'] and instances[-1].closed
    auth['authMethod']='apiKey'
    with pytest.raises(NoteFailure) as error: bridge.claude_generate({'executable':'unused'},[],tmp_path,None)
    assert error.value.code == 'provider_authentication' and len(instances) == 1


def test_subscription_unexpected_tool_request_fails_closed(tmp_path, monkeypatch):
    sent=[]
    class Client:
        def __init__(self,*args): pass
        def send(self,event): sent.append(event)
        def event(self): return {'id':99,'method':'item/commandExecution/requestApproval','params':{}}
        def close(self): pass
    monkeypatch.setattr(bridge,'ClientProcess',Client)
    with pytest.raises(NoteFailure) as error:
        bridge.codex_generate({'executable':'unused'},[],tmp_path,None)
    assert error.value.code == 'unexpected_tool_request'
    assert sent[-1]['error']['code'] == -32601
