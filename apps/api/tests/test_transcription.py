import json
from datetime import timedelta
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from test_workspace import setup, login, course, lecture
from test_capture import capture, upload, seal
from notetaker.models import (Lecture, Job, SpeechWindow, SpeechGeneration, TranscriptVersion,
    TranscriptSnapshot, CaptureRun, Outbox, Inbox, Session, Owner, now)
from notetaker.transcription import lock_lecture, schedule
from notetaker.speech_worker import plan_pending, claim, execute, publish, renew, dispatch, consume_event, event_payload, pause_cut
from notetaker.speech_provider import SpeechFailure, validate_result, owned_words, WhisperProvider


class FakeSpeech:
    def __init__(self, after=None, failure=None):self.after,self.failure=after,failure
    def transcribe(self, audio, window, rate):
        if self.after:self.after()
        if self.failure:raise self.failure
        return result(window)


def result(window):
    return {'outcome':'speech','segments':[{'text':'Binary search requires a sorted array.',
        'start_sample':window.core_start,'end_sample':min(window.core_end,window.core_start+48000),
        'confidence':{'kind':'unavailable','value':None}}],'metadata':{'provider':'synthetic-test-double'}}


@pytest.fixture
def speech(capture):
    app,client,headers,path,run=capture
    for sequence in range(3):
        assert upload(client,headers,path,run,sequence,count=480000).status_code==200
    assert seal(client,headers,path,run,last=2,samples=1440000).status_code==200
    plan_pending(app.state.sessions)
    return capture


def finish_all(app):
    while chosen:=claim(app.state.sessions):
        assert execute(app.state.sessions,app.state.audio_store,FakeSpeech(),chosen,heartbeat=False)


def test_sealed_context_windows_cover_once_and_chunk_jobs_wait(speech):
    app,client,headers,path,run=speech
    with app.state.sessions() as db:
        windows=db.scalars(select(SpeechWindow).order_by(SpeechWindow.core_start)).all()
        assert [(w.core_start,w.core_end,w.context_start,w.context_end) for w in windows]==[
            (0,1152000,0,1248000),(1152000,1440000,1056000,1440000)]
        assert all(j.status=='due' for j in db.scalars(select(Job).where(Job.kind=='speech.chunk')))
    finish_all(app)
    data=client.get(path+'/transcript').json()
    assert data['status']=='processed' and len(data['snapshot']['segments'])==2
    with app.state.sessions() as db:
        assert all(j.status=='completed' for j in db.scalars(select(Job)))
        assert db.scalar(select(func.count()).select_from(SpeechGeneration))==2
    plan_pending(app.state.sessions)
    assert claim(app.state.sessions) is None


def test_unsealed_or_missing_audio_never_becomes_silence(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,count=48000)
    plan_pending(app.state.sessions)
    assert claim(app.state.sessions) is None
    assert seal(client,headers,path,run,last=1,samples=96000).status_code==200
    plan_pending(app.state.sessions)
    assert claim(app.state.sessions) is None
    assert client.get(path+'/transcript').json()['status']=='awaiting_saved_audio'


def test_windows_do_not_cross_declared_gaps(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,count=1440000)
    seal(client,headers,path,run,samples=1440000,gaps=[{'reason':'microphone_lost','after_sample':720000,'unknown_extent':True}])
    plan_pending(app.state.sessions)
    with app.state.sessions() as db:
        windows=db.scalars(select(SpeechWindow).order_by(SpeechWindow.core_start)).all()
        assert [(w.context_start,w.context_end) for w in windows]==[(0,720000),(720000,1440000)]


def test_concurrent_delivery_only_one_lecture_claim(speech):
    app,*_=speech
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:claim(app.state.sessions),range(2)))
    assert sum(r is not None for r in results)==1


def test_expired_attempt_cannot_publish_after_reclaim(speech):
    app,*_=speech
    old=claim(app.state.sessions)
    with app.state.sessions() as db:
        db.get(Job,old[0]).lease_expires_at=now()-timedelta(seconds=1);db.commit()
    new=claim(app.state.sessions,old[0])
    assert new[1]!=old[1]
    with app.state.sessions() as db: window=db.get(SpeechWindow,db.get(Job,old[0]).input_revision)
    assert not publish(app.state.sessions,*old,result(window))
    assert execute(app.state.sessions,app.state.audio_store,FakeSpeech(),new,heartbeat=False)
    assert not publish(app.state.sessions,*new,result(window))
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(SpeechGeneration))==1


def test_lease_renewal_keeps_current_attempt(speech):
    app,*_=speech
    chosen=claim(app.state.sessions)
    assert renew(app.state.sessions,*chosen)
    assert not renew(app.state.sessions,chosen[0],str(uuid4()))
    assert claim(app.state.sessions) is None


def test_worker_process_exit_leaves_reclaimable_job(speech):
    import os,subprocess,sys
    app,*_=speech
    child_code='''
import json,time,os
from notetaker.db import database
from notetaker.speech_worker import claim
_,sessions=database(os.environ['SYNTHETIC_TEST_DATABASE'])
chosen=claim(sessions)
print(json.dumps(chosen),flush=True)
time.sleep(120)
'''
    child=subprocess.Popen([sys.executable,'-c',child_code],env={**os.environ,
        'SYNTHETIC_TEST_DATABASE':app.state.settings.database_url},stdout=subprocess.PIPE,text=True)
    try:
        import threading,queue
        output=queue.Queue()
        threading.Thread(target=lambda:output.put(child.stdout.readline()),daemon=True).start()
        old=json.loads(output.get(timeout=20))
        assert old
    finally:
        child.terminate();child.wait(timeout=10);child.stdout.close()
    # Accelerate lease expiry in the isolated test DB; this is not a wall-clock timeout measurement.
    with app.state.sessions() as db:
        job=db.get(Job,old[0]);assert job.status=='running'
        job.lease_expires_at=now()-timedelta(seconds=1);db.commit()
    new=claim(app.state.sessions,old[0]);assert new and new[1]!=old[1]
    assert execute(app.state.sessions,app.state.audio_store,FakeSpeech(),new,heartbeat=False)


@pytest.mark.parametrize('change',['delete','audio_epoch','manifest'])
def test_output_is_fenced_when_sources_change_during_inference(speech,change):
    app,client,headers,path,run=speech
    def mutate():
        with app.state.sessions() as db:
            if change=='delete':db.get(Lecture,run['lecture_id']).tombstoned=True
            elif change=='audio_epoch':db.get(Lecture,run['lecture_id']).audio_epoch+=1
            else:db.get(CaptureRun,run['id']).manifest_version+=1
            db.commit()
    assert not execute(app.state.sessions,app.state.audio_store,FakeSpeech(after=mutate),claim(app.state.sessions),heartbeat=False)
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(TranscriptVersion))==0


@pytest.mark.parametrize('failure,status',[('model_unavailable','due'),('speech_output_invalid','failed')])
def test_failure_retains_audio_and_reports_retry_state(speech,failure,status):
    app,client,headers,path,run=speech
    chosen=claim(app.state.sessions)
    assert not execute(app.state.sessions,app.state.audio_store,
        FakeSpeech(failure=SpeechFailure(failure,failure=='model_unavailable')),chosen,heartbeat=False)
    with app.state.sessions() as db:
        assert db.get(Job,chosen[0]).status==status
        assert db.scalar(select(func.count()).select_from(TranscriptVersion))==0
    assert failure in client.get(path+'/transcript').json()['errors']
    assert client.post(path+'/transcription',headers=headers).status_code==200
    assert claim(app.state.sessions,chosen[0])


def test_audio_integrity_failure_never_calls_model(speech):
    app,*_=speech
    app.state.audio_store.objects={k:b'corrupt' for k in app.state.audio_store.objects}
    provider=FakeSpeech(after=lambda:pytest.fail('model must not receive corrupt audio'))
    chosen=claim(app.state.sessions)
    assert not execute(app.state.sessions,app.state.audio_store,provider,chosen,heartbeat=False)
    with app.state.sessions() as db:assert db.get(Job,chosen[0]).error_code=='audio_integrity_unavailable'


def test_correction_versions_idempotency_conflict_and_audio(speech):
    app,client,headers,path,run=speech
    assert execute(app.state.sessions,app.state.audio_store,FakeSpeech(),claim(app.state.sessions),heartbeat=False)
    old=client.get(path+'/transcript').json()['snapshot']
    passage=old['segments'][0];endpoint=path+'/transcript/segments/'+passage['segment_id']+'/corrections'
    body={'expected_version':passage['id'],'text':'Binary search requires sorted input, not merely distinct input.'}
    corrected=client.post(endpoint,json=body,headers=headers)
    assert corrected.status_code==200,corrected.text
    assert client.post(endpoint,json=body,headers=headers).json()==corrected.json()
    assert client.post(endpoint,json={**body,'text':'different'},headers=headers).status_code==409
    assert client.post(endpoint,json=body,headers={**headers,'idempotency-key':str(uuid4())}).status_code==409
    assert client.post(endpoint,json={'text':'missing base'},headers=headers).status_code==428
    assert client.post(endpoint,json=body,headers={'origin':headers['origin']}).status_code==403
    # A later window publication retains the human revision; old source and snapshot remain readable.
    finish_all(app)
    latest=client.get(path+'/transcript').json()['snapshot']
    assert latest['segments'][0]['id']==corrected.json()['id']
    assert latest['segments'][0]['author']=='student'
    assert len(client.get(path+'/transcript/segments/'+passage['segment_id']+'/versions').json())==2
    assert client.get(path+'/transcript/snapshots/'+old['id']).json()['segments'][0]['text']==passage['text']
    assert client.get(path+'/sources/'+passage['id']).json()['text']==passage['text']
    audio=client.get(path+'/sources/'+passage['id']+'/audio')
    assert audio.status_code==200 and audio.content[:4]==b'RIFF'


def test_source_and_correction_are_scoped_to_lecture(speech):
    app,client,headers,path,run=speech
    finish_all(app)
    segment=client.get(path+'/transcript').json()['snapshot']['segments'][0]
    another=lecture(client,headers,course(client,headers)['id'])
    other=f"/lectures/{another['id']}"
    assert client.get(other+'/sources/'+segment['id']).status_code==404
    assert client.get(other+'/sources/'+segment['id']+'/audio').status_code==404
    assert client.post(other+'/transcript/segments/'+segment['segment_id']+'/corrections',
        headers=headers,json={'expected_version':segment['id'],'text':'wrong parent'}).status_code==404
    client.post('/session/logout',headers=headers)
    assert client.get(path+'/transcript').status_code==401
    assert client.get(path+'/sources/'+segment['id']).status_code==401


def test_playback_rechecks_authentication_after_object_read(speech):
    app,client,headers,path,run=speech;finish_all(app)
    segment=client.get(path+'/transcript').json()['snapshot']['segments'][0]
    original=app.state.audio_store.read
    def revoke(key):
        data=original(key)
        with app.state.sessions() as db:
            for session in db.scalars(select(Session)):session.revoked=True
            db.commit()
        return data
    app.state.audio_store.read=revoke
    assert client.get(path+'/sources/'+segment['id']+'/audio').status_code==401


def test_outbox_and_inbox_duplicate_delivery_use_same_job(speech):
    app,*_=speech
    class Producer:
        def __init__(self):self.sent=[]
        def produce(self,topic,key,value,on_delivery):self.sent.append(json.loads(value));on_delivery(None,None)
        def flush(self,timeout):return 0
    producer=Producer()
    assert dispatch(app.state.sessions,producer)
    events=[p for p in producer.sent if p['event_type']=='speech.requested']
    assert len(events)==2 and all('text' not in p for p in producer.sent)
    first=consume_event(app.state.sessions,events[0])
    assert consume_event(app.state.sessions,events[0])==first
    assert consume_event(app.state.sessions,{**events[0],'lecture_id':str(uuid4())}) is None
    assert consume_event(app.state.sessions,{**events[0],'text':'untrusted'}) is None
    assert claim(app.state.sessions,first)
    assert claim(app.state.sessions,first) is None
    with app.state.sessions() as db:assert db.scalar(select(func.count()).select_from(Inbox))==1


def test_midpoint_ownership_preserves_real_repetitions():
    words=[SimpleNamespace(start=23.7,end=23.9,word=' repeat',probability=.8),
        SimpleNamespace(start=24.1,end=24.3,word=' repeat',probability=.8)]
    segment=SimpleNamespace(words=words)
    first=SimpleNamespace(context_start=0,context_end=26000,core_start=0,core_end=24000)
    second=SimpleNamespace(context_start=0,context_end=30000,core_start=24000,core_end=30000)
    assert owned_words([segment],first,1000)[0]['text']=='repeat'
    assert owned_words([segment],second,1000)[0]['text']=='repeat'


def test_provider_normalizes_numeric_scalars_before_strict_validation():
    class ProviderScalar(float): pass
    window=SimpleNamespace(context_start=0,context_end=48000,core_start=0,core_end=48000)
    word=SimpleNamespace(start=ProviderScalar(0),end=ProviderScalar(.5),word=' search',probability=ProviderScalar(.9))
    segments=owned_words([SimpleNamespace(words=[word])],window,48000)
    assert type(segments[0]['confidence']['value']) is float
    validate_result({'outcome':'speech','segments':segments},window)


def test_pause_planning_uses_audio_and_keeps_word_repetitions():
    import io,wave,array
    rate=8000;pcm=array.array('h',[5000]*32000)
    pcm[12000:15200]=array.array('h',[0]*3200)
    audio=io.BytesIO()
    with wave.open(audio,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm.tobytes())
    cut=pause_cut(audio.getvalue(),rate,24*rate,22*rate)
    assert 23.5*rate<cut<23.9*rate


@pytest.mark.parametrize('change',['reversed','outside','nan','empty','silence_text'])
def test_invalid_provider_results_rejected(change):
    window=SimpleNamespace(core_start=0,core_end=96000)
    data=result(window)
    if change=='reversed':data['segments'][0]['end_sample']=0
    elif change=='outside':data['segments'][0]['end_sample']=100000
    elif change=='nan':data['segments'][0]['confidence']={'kind':'uncalibrated_score','value':float('nan')}
    elif change=='empty':data['segments']=[]
    else:data['outcome']='silence'
    with pytest.raises(SpeechFailure):validate_result(data,window)


def test_missing_local_model_does_not_download(tmp_path):
    provider=WhisperProvider(SimpleNamespace(speech_model_path=str(tmp_path/'missing'),speech_threads=1))
    with pytest.raises(SpeechFailure,match='model_unavailable'):provider.load()

