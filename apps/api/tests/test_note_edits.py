import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import select
from test_notes import notes, speech, FakeNotes, correction
from test_transcription import finish_all
from test_capture import capture
from test_workspace import setup
from notetaker.note_worker import plan, claim, execute
from notetaker.models import NoteEdit


def generated(app, client, path):
    plan(app.state.sessions)
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    return client.get(path+'/notes').json()['revision']


def command(client, headers, path, body, key=None):
    return client.post(path+'/notes/edits', headers={**headers,'idempotency-key':key or str(uuid4())},json=body)


def saved_edit(notes):
    app,client,headers,path,_=notes
    revision=generated(app,client,path)
    body={'expected_version':0,'base_id':revision['id'],'action':'save',
        'passages':[{'id':revision['content']['blocks'][0]['passages'][0]['id'],'text':'My reasoning:\n    lo = mid + 1\nE = mc²'}]}
    response=command(client,headers,path,body)
    assert response.status_code==200,response.text
    return revision,response.json(),body


def test_edit_and_failed_response_retry_preserve_export(notes):
    app,client,headers,path,_=notes
    revision=generated(app,client,path)
    old=client.get(path+'/notes/revisions/'+revision['id']+'/export').text
    body={'expected_version':0,'base_id':revision['id'],'action':'save','additional_text':'My own <script> notes\n    x = 1'}
    key=str(uuid4())
    first=command(client,headers,path,body,key)
    retry=command(client,headers,path,body,key)
    assert first.status_code==200 and first.json()==retry.json()
    selected=client.get(path+'/notes').json()['editing']['selected']
    assert selected['student'] and selected['content']['blocks'][-1]['passages'][0]['student_edited']
    export=client.get(path+'/notes/edits/'+selected['id']+'/export')
    assert 'Student study notes' in export.text and '&lt;script&gt;' in export.text
    assert client.get(path+'/notes/revisions/'+revision['id']+'/export').text==old
    assert command(client,headers,path,{**body,'additional_text':'different'},key).status_code==409


def test_generation_during_edit_becomes_proposal(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    correction(client,headers,path);plan(app.state.sessions)
    def during():
        response=command(client,headers,path,{'expected_version':0,'base_id':base['id'],'action':'save','additional_text':'Protect this student text.'})
        assert response.status_code==200
    assert execute(app.state.sessions,FakeNotes(after=during),claim(app.state.sessions),heartbeat=False)
    state=client.get(path+'/notes').json()
    assert state['editing']['proposal']['id']==state['revision']['id']
    assert 'Protect this student text.' in json.dumps(state['editing']['selected']['content'])
    assert state['editing']['proposal_valid']


def test_concurrent_edits_and_stale_comparison_conflict(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    body={'expected_version':0,'base_id':base['id'],'action':'save','additional_text':'student'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:command(client,headers,path,body),range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    selected=client.get(path+'/notes').json()['editing']['selected']
    correction(client,headers,path);proposal=generated(app,client,path)
    newer=command(client,headers,path,{'expected_version':1,'base_id':selected['id'],'action':'save','additional_text':'newer edit'})
    assert newer.status_code==200
    stale=command(client,headers,path,{'expected_version':1,'base_id':selected['id'],'action':'replace','proposal_id':proposal['id']})
    assert stale.status_code==409
    assert client.get(path+'/notes').json()['editing']['selected']['id']==newer.json()['id']


def test_merge_keep_replace_and_undo_are_immutable(notes):
    app,client,headers,path,_=notes
    base,edit,_=saved_edit(notes)
    correction(client,headers,path);proposal=generated(app,client,path)
    merged=command(client,headers,path,{'expected_version':1,'base_id':edit['id'],'action':'merge','proposal_id':proposal['id'],'block_ids':[proposal['content']['blocks'][0]['id']]})
    assert merged.status_code==200,merged.text
    merged=merged.json()
    assert 'My reasoning:' in json.dumps(merged['content']) and 'only works' in json.dumps(merged['content'])
    exported=client.get(path+'/notes/edits/'+merged['id']+'/export').text
    assert 'Student study notes' in exported and 'My reasoning:' in exported and 'only works' in exported
    assert 'E = mc²' in exported and 'lo = mid' in exported
    replaced=command(client,headers,path,{'expected_version':2,'base_id':merged['id'],'action':'replace','proposal_id':proposal['id']}).json()
    assert replaced['content']==proposal['content']
    undone=command(client,headers,path,{'expected_version':3,'base_id':replaced['id'],'action':'undo','target_id':edit['id']}).json()
    assert undone['content']==edit['content'] and undone['revision']==4
    kept=command(client,headers,path,{'expected_version':4,'base_id':undone['id'],'action':'keep','proposal_id':proposal['id']}).json()
    assert kept['content']==edit['content']
    assert client.get(path+'/notes').json()['editing']['proposal'] is None
    assert client.get(path+'/notes/edits/'+merged['id']+'/export').text==exported
    with app.state.sessions() as db: assert len(db.scalars(select(NoteEdit)).all())==5


def test_source_and_setting_changes_invalidate_suggestions(notes):
    app,client,headers,path,_=notes
    base,edit,_=saved_edit(notes)
    correction(client,headers,path);proposal=generated(app,client,path)
    correction(client,headers,path,'A newer corrected source.')
    state=client.get(path+'/notes').json()
    assert not state['editing']['proposal_valid'] and state['editing']['sources_changed']
    body={'expected_version':1,'base_id':edit['id'],'action':'replace','proposal_id':proposal['id']}
    assert command(client,headers,path,body).status_code==409
    proposal=generated(app,client,path)
    response=client.post(path+'/notes/model',headers={**headers,'idempotency-key':str(uuid4())},json={
        'expected_version':1,'model':'qwen3:4b','detail_prompt':'Include all steps.'})
    assert response.status_code==200
    assert not client.get(path+'/notes').json()['editing']['proposal_valid']
    assert command(client,headers,path,{**body,'proposal_id':proposal['id']}).status_code==409


def test_edit_authority_validation_and_cross_lecture_history(notes):
    app,client,headers,path,_=notes
    base,edit,body=saved_edit(notes)
    assert client.post(path+'/notes/edits',json=body).status_code==403
    body={**body,'expected_version':1,'base_id':edit['id'],'passages':[{'id':'foreign','text':'injection'}]}
    assert command(client,headers,path,body).status_code==422
    assert client.get('/lectures/'+str(uuid4())+'/notes/edits/'+edit['id']+'/export').status_code==404
    assert command(client,headers,path,{**body,'action':'undo','target_id':str(uuid4())}).status_code==404
    client.cookies.clear()
    for suffix in ('/notes/history','/notes/edits/'+edit['id']+'/export','/notes/stream'):
        assert client.get(path+suffix).status_code==401
