from uuid import uuid4
from sqlalchemy import select, func
from test_workspace import setup, login, course, lecture
from test_capture import capture, upload, seal
from test_transcription import speech, finish_all, FakeSpeech
from test_notes import notes, FakeNotes, correction
from test_note_edits import generated, command
from notetaker import models as m
from notetaker.lifecycle import reconcile_finalizations, reconcile_deletion
from notetaker.note_worker import claim, execute, plan
from notetaker.speech_worker import claim as speech_claim, execute as speech_execute


def finalize(client,headers,path,available=False,key=None):
    state=client.get(path+'/finalization').json()
    return client.post(path+'/finalization',headers={**headers,'idempotency-key':key or str(uuid4())},json={'expected_cursor':state['cursor'],'expected_edit_version':state['edit_version'],'available_only':available})


def remove(client,headers,path,kind='lecture'):
    state=client.get(path+'/finalization').json()
    return client.post(path+'/deletion',headers={**headers,'idempotency-key':str(uuid4())},json={'expected_cursor':state['cursor'],'kind':kind})


def test_finalization_coordinates_final_notes_and_keeps_immutable_history(notes):
    app,client,headers,path,run=notes
    original=generated(app,client,path)
    response=finalize(client,headers,path)
    assert response.status_code==202,response.text
    plan(app.state.sessions)
    chosen=claim(app.state.sessions)
    if chosen:assert execute(app.state.sessions,FakeNotes(),chosen,heartbeat=False)
    reconcile_finalizations(app.state.sessions)
    result=client.get(path+'/finalization').json()['history'][0]
    assert result['status']=='complete',result
    url=path+'/final-snapshots/'+result['snapshot_id']
    frozen=client.get(url).json();export=client.get(url+'/export').text
    correction(client,headers,path)
    assert client.get(url).json()==frozen
    assert client.get(url+'/export').text==export
    assert client.get(path+'/notes/revisions/'+original['id']+'/export').status_code==200
    assert upload(client,headers,path,run,3,count=480000).status_code==409


def test_finalization_includes_verified_audio_after_a_missing_chunk(capture):
    app,client,headers,path,run=capture
    assert upload(client,headers,path,run,0,count=48000).status_code==200
    assert upload(client,headers,path,run,2,count=48000).status_code==200
    assert seal(client,headers,path,run,last=2,samples=144000).status_code==200
    response=finalize(client,headers,path)
    assert response.status_code==202,response.text
    with app.state.sessions() as db:
        windows=db.scalars(select(m.SpeechWindow).order_by(m.SpeechWindow.core_start)).all()
        assert [(w.core_start,w.core_end) for w in windows]==[(0,48000),(96000,144000)]
    finish_all(app);reconcile_finalizations(app.state.sessions)
    state=client.get(path+'/finalization').json()['history'][0]
    assert state['status']=='incomplete' and state['issues']
    assert len(client.get(path+'/final-snapshots/'+state['snapshot_id']).json()['transcript']['segments'])==2


def test_finalization_protects_edits_made_while_processing(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    correction(client,headers,path)
    assert finalize(client,headers,path).status_code==202
    response=command(client,headers,path,{'action':'save','expected_version':0,'base_id':base['id'],'additional_text':'Keep my newest edit.'})
    assert response.status_code==200,response.text
    reconcile_finalizations(app.state.sessions)
    state=client.get(path+'/finalization').json()['history'][0]
    assert state['status']=='needs_attention' and not state['snapshot_id']
    saved=finalize(client,headers,path,True).json()
    assert saved['snapshot_id']
    snapshot=client.get(path+'/final-snapshots/'+saved['snapshot_id']).json()
    assert snapshot['notes']['student'] and 'Keep my newest edit.' in str(snapshot)


def test_audio_removal_preserves_revisions_and_sources_but_fences_worker(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    before=client.get(path+'/notes/revisions/'+base['id']+'/export').text
    source=client.get(path+'/transcript').json()['snapshot']['segments'][0]
    correction(client,headers,path);plan(app.state.sessions);chosen=claim(app.state.sessions)
    row=remove(client,headers,path,'audio').json()
    assert not execute(app.state.sessions,FakeNotes(),chosen,heartbeat=False)
    reconcile_deletion(app.state.sessions,app.state.audio_store,row['id'])
    assert not app.state.audio_store.objects
    assert client.get(path+'/sources/'+source['id']).status_code==200
    assert client.get(path+'/sources/'+source['id']+'/audio').status_code==404
    assert client.get(path+'/notes/revisions/'+base['id']+'/export').text==before
    assert client.get(path+'/transcript').json()['snapshot']['segments']
    correction(client,headers,path,'Corrected after audio removal.')
    assert client.get(path+'/transcript').json()['snapshot']['segments'][0]['text']=='Corrected after audio removal.'


def test_lecture_deletion_retries_storage_and_reconciles_late_objects(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    command(client,headers,path,{'action':'save','expected_version':0,'base_id':base['id'],'additional_text':'Remove this private draft.'})
    finalize(client,headers,path,True)
    object_key=next(iter(app.state.audio_store.objects))
    row=remove(client,headers,path).json()
    assert client.get(path+'/snapshot').status_code==404
    app.state.audio_store.fail=True
    reconcile_deletion(app.state.sessions,app.state.audio_store,row['id'])
    assert client.get('/deletions').json()[0]['status']=='retrying'
    app.state.audio_store.fail=False
    reconcile_deletion(app.state.sessions,app.state.audio_store,row['id'])
    assert client.get('/deletions').json()[0]['status']=='complete'
    assert not app.state.audio_store.objects
    with app.state.sessions() as db:
        for model in (m.NoteEdit,m.NoteRevision,m.NoteRequest,m.TranscriptVersion,m.FinalSnapshot,m.CaptureRun,m.UploadReservation):
            assert db.scalar(select(func.count()).select_from(model))==0,model
        assert db.get(m.Lecture,path.split('/')[-1]).tombstoned
    app.state.audio_store.objects[object_key]=b'late upload after tombstone'
    reconcile_deletion(app.state.sessions,app.state.audio_store,row['id'])
    assert not app.state.audio_store.objects
    assert client.get(path+'/notes').status_code==404


def test_deletion_during_upload_cannot_recreate_content(capture):
    app,client,headers,path,run=capture
    ids=[]
    def during():
        row=remove(client,headers,path).json();ids.append(row['id'])
    app.state.audio_store.after_write=during
    assert upload(client,headers,path,run).status_code==404
    reconcile_deletion(app.state.sessions,app.state.audio_store,ids[0])
    assert not app.state.audio_store.objects


def test_finalization_expected_version_and_origin_fences(setup):
    app,client,_=setup;headers=login(client);lec=lecture(client,headers,course(client,headers)['id']);path='/lectures/'+lec['id']
    body={'expected_cursor':0,'expected_edit_version':0}
    assert client.post(path+'/finalization',json=body,headers=headers).status_code==409
    assert client.post(path+'/deletion',json={'kind':'lecture','expected_cursor':1},headers={'origin':headers['origin']}).status_code==403
    saved=finalize(client,headers,path,True)
    assert saved.status_code==202 and saved.json()['status']=='incomplete'


def test_reopen_recovers_late_audio_without_mutating_final_snapshot(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,0,count=48000)
    first=finalize(client,headers,path,True).json()
    url=path+'/final-snapshots/'+first['snapshot_id']
    before=client.get(url).json()
    assert upload(client,headers,path,run,1,count=48000).status_code==409
    state=client.get(path+'/finalization').json()
    response=client.post(path+'/finalization/reopen',headers={**headers,'idempotency-key':str(uuid4())},json={'expected_cursor':state['cursor'],'expected_edit_version':state['edit_version']})
    assert response.status_code==200,response.text
    capture_state=client.get(path+'/capture').json()
    manifest=client.get(path+'/capture-runs/'+run['id']+'/manifest').json()
    grant='late-recovery-'+uuid4().hex
    response=client.post(path+'/capture-recovery',headers={**headers,'idempotency-key':str(uuid4())},json={
        'run_id':run['id'],'grant':grant,'expected_capture_epoch':capture_state['capture_epoch'],'expected_version':manifest['manifest_version'],
        'last_sequence':1,'final_sample_count':96000,'gaps':[],'interrupted':True})
    assert response.status_code==200,response.text
    assert upload(client,{**headers,'x-capture-grant':grant},path,run,1,count=48000).status_code==200
    assert client.get(url).json()==before
    second=finalize(client,headers,path,True).json()
    assert second['snapshot_id']!=first['snapshot_id']
    assert client.get(url).json()==before


def test_audio_removal_still_allows_transcript_only_regeneration(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    row=remove(client,headers,path,'audio').json()
    reconcile_deletion(app.state.sessions,app.state.audio_store,row['id'])
    state=client.get(path+'/notes').json()
    response=client.post(path+'/notes/model',headers={**headers,'idempotency-key':str(uuid4())},json={'expected_version':state['preference']['version'],'model':'qwen3:4b','enabled':True,'instructions':'Explain fully'})
    assert response.status_code==200,response.text
    plan(app.state.sessions)
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
    assert client.get(path+'/notes').json()['revision']['id']!=base['id']
    assert not app.state.audio_store.objects


def test_deleted_speech_attempt_cannot_publish_after_inventory_erasure(speech):
    from notetaker.speech_worker import publish
    app,client,headers,path,_=speech
    chosen=speech_claim(app.state.sessions)
    row=remove(client,headers,path).json()
    reconcile_deletion(app.state.sessions,app.state.audio_store,row['id'])
    assert not publish(app.state.sessions,*chosen,{})


def test_failed_notes_leave_history_and_offer_available_finalization(notes):
    app,client,headers,path,_=notes
    base=generated(app,client,path)
    correction(client,headers,path)
    finalize(client,headers,path)
    plan(app.state.sessions)
    assert not execute(app.state.sessions,FakeNotes(corrupt=True),claim(app.state.sessions),heartbeat=False)
    reconcile_finalizations(app.state.sessions)
    state=client.get(path+'/finalization').json()['history'][0]
    assert state['status']=='needs_attention'
    assert client.get(path+'/notes/revisions/'+base['id']+'/export').status_code==200
    available=finalize(client,headers,path,True).json()
    assert available['status']=='incomplete' and available['snapshot_id']


def test_real_object_deletion_and_late_upload_reconciliation(capture):
    import os
    import pytest
    from notetaker.audio_store import AudioStore
    if not os.environ.get('NOTETAKER_TEST_DATABASE_URL'):
        pytest.skip('Real object deletion is exercised with the PostgreSQL/service run.')
    app,client,headers,path,run=capture
    bucket='m07-delete-'+uuid4().hex
    store=AudioStore(app.state.settings.model_copy(update={'audio_bucket':bucket,'preview':False}))
    assert store.available
    app.state.audio_store=store
    store.ready()
    try:
        assert upload(client,headers,path,run).status_code==200
        keys=store.list_keys(path.split('/')[-1]+'/');assert len(keys)==1
        row=remove(client,headers,path).json()
        reconcile_deletion(app.state.sessions,store,row['id'])
        assert store.list_keys(path.split('/')[-1]+'/')==[]
        # Simulate an upload whose object write finished after its reservation was erased.
        store.client.put_object(Bucket=bucket,Key=keys[0],Body=b'synthetic late object')
        reconcile_deletion(app.state.sessions,store,row['id'])
        assert store.list_keys(path.split('/')[-1]+'/')==[]
        assert client.get('/deletions').json()[0]['status']=='complete'
    finally:
        for key in store.list_keys(''):store.delete_verified(key)
        store.client.delete_bucket(Bucket=bucket)
