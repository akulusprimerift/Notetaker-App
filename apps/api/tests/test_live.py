"""M05 synthetic integration: real API/database/worker contracts, fake local models."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, func, delete
from starlette.websockets import WebSocketDisconnect
from test_workspace import setup, ORIGIN
from test_capture import capture, upload, seal
from test_transcription import FakeSpeech, finish_all
from test_notes import FakeNotes, notes, speech
from notetaker.models import (Job, SpeechWindow, LectureUpdate, TranscriptSnapshot, NoteRequest,
    NoteRevision, Session, now)
from notetaker.speech_worker import plan_pending, claim as speech_claim, execute as speech_execute
from notetaker.note_worker import plan, claim, execute
from notetaker.note_draft import draft_messages
from notetaker.resource_budget import inference_slot


def enable(app, client, headers, path):
    app.state.note_provider = FakeNotes()
    response = client.post(path+'/notes/model', headers={**headers, 'idempotency-key':str(uuid4())},
        json={'expected_version':0, 'model':'qwen3:4b'})
    assert response.status_code == 200


def append(app, client, headers, path, run, sequence):
    assert upload(client,headers,path,run,sequence,count=1440000).status_code == 200
    plan_pending(app.state.sessions)
    finish_all(app)


def test_live_capture_notes_and_seal_reuse_sources(capture):
    app,client,headers,path,run = capture
    enable(app,client,headers,path)
    append(*capture,0)
    transcript = client.get(path+'/transcript').json()
    assert transcript['mode'] == 'live'
    assert transcript['snapshot']['stability'] == 'provisional'
    assert transcript['processing_delay_seconds'] == 6
    original = transcript['snapshot']['segments'][0]
    plan(app.state.sessions)
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
    assert client.get(path+'/notes').json()['revision']
    append(*capture,1)
    assert seal(client,headers,path,run,last=1,samples=2880000).status_code == 200
    plan_pending(app.state.sessions); finish_all(app)
    final = client.get(path+'/transcript').json()
    assert final['snapshot']['stability'] == 'stable'
    assert final['processing_delay_seconds'] == 0
    assert final['snapshot']['segments'][0]['id'] == original['id']
    with app.state.sessions() as db:
        windows = db.scalars(select(SpeechWindow).order_by(SpeechWindow.core_start)).all()
        assert [(w.core_start//48000,w.core_end//48000) for w in windows] == [(0,24),(24,48),(48,60)]
        before = db.scalar(select(func.count()).select_from(TranscriptSnapshot))
    plan_pending(app.state.sessions)
    with app.state.sessions() as db: assert db.scalar(select(func.count()).select_from(TranscriptSnapshot)) == before


def test_missing_prefix_does_not_schedule_live_audio(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,1,count=1440000)
    plan_pending(app.state.sessions)
    assert speech_claim(app.state.sessions) is None
    append(*capture,0)
    assert client.get(path+'/transcript').json()['snapshot']['segments']


def test_late_gap_replaces_crossing_live_window_and_fences_result(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,count=1440000)
    plan_pending(app.state.sessions)
    chosen=speech_claim(app.state.sessions)
    seal(client,headers,path,run,samples=1440000,gaps=[{'reason':'microphone_lost','after_sample':720000,'unknown_extent':True}])
    assert not speech_execute(app.state.sessions,app.state.audio_store,FakeSpeech(),chosen,heartbeat=False)
    # Reconciliation cancels the stale claim before attempting current windows.
    with app.state.sessions() as db:
        db.get(Job,chosen[0]).lease_expires_at=now()-timedelta(seconds=1);db.commit()
    plan_pending(app.state.sessions);finish_all(app)
    segments=client.get(path+'/transcript').json()['snapshot']['segments']
    assert len(segments)==2 and all(p['end_sample']<=720000 or p['start_sample']>=720000 for p in segments)


def test_pending_notes_coalesce_and_keep_latest_snapshot(capture):
    app,client,headers,path,run=capture
    enable(app,client,headers,path)
    for sequence in range(3):
        append(*capture,sequence);plan(app.state.sessions)
    with app.state.sessions() as db:
        jobs=db.scalars(select(Job).where(Job.kind=='notes.generate')).all()
        assert sum(j.status=='due' for j in jobs)==1
        assert sum(j.status=='cancelled' for j in jobs)==2
        latest=db.scalar(select(TranscriptSnapshot).order_by(TranscriptSnapshot.sequence.desc()).limit(1))
        due=next(j for j in jobs if j.status=='due')
        assert db.get(NoteRequest,due.input_revision).snapshot_id==latest.id
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)


def test_shared_budget_blocks_both_workers_but_not_audio_upload(capture):
    app,client,headers,path,run=capture
    enable(app,client,headers,path);append(*capture,0);plan(app.state.sessions)
    assert upload(client,headers,path,run,1,count=1440000).status_code==200
    plan_pending(app.state.sessions)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda f:f(app.state.sessions),[claim,speech_claim]))
    assert sum(r is not None for r in results)==1
    assert claim(app.state.sessions) is None and speech_claim(app.state.sessions) is None
    assert upload(client,headers,path,run,2,count=1440000).status_code==200
    # A process still performing inference cannot overlap a reclaimed job.
    with inference_slot(app.state.sessions) as first:
        with inference_slot(app.state.sessions) as second:
            assert first and not second


def test_speech_model_outage_leaves_capture_and_replay_available(capture):
    from notetaker.speech_provider import SpeechFailure
    app,client,headers,path,run=capture
    upload(client,headers,path,run,count=1440000);plan_pending(app.state.sessions)
    chosen=speech_claim(app.state.sessions)
    assert not speech_execute(app.state.sessions,app.state.audio_store,FakeSpeech(failure=SpeechFailure('model_unavailable')),chosen,heartbeat=False)
    assert upload(client,headers,path,run,1,count=1440000).status_code==200
    with client.websocket_connect(path+'/updates?after=0',headers={'origin':ORIGIN}) as ws:
        assert ws.receive_json()['kind']=='updates'
    with app.state.sessions() as db:
        db.get(Job,chosen[0]).due_at=now();db.commit()
    plan_pending(app.state.sessions);finish_all(app)
    assert client.get(path+'/transcript').json()['counts']['completed']==2


def test_websocket_replay_reset_and_session_revocation(capture):
    app,client,headers,path,run=capture
    head=client.get(path+'/snapshot').json()['update_cursor']
    upload(client,headers,path,run,count=1440000)
    with client.websocket_connect(path+f'/updates?after={head}',headers={'origin':ORIGIN}) as ws:
        batch=ws.receive_json()
        assert batch['events'][0]['sequence']==head+1
        assert batch['cursor']==client.get(path+'/snapshot').json()['update_cursor']
        with app.state.sessions() as db:
            db.scalar(select(Session)).revoked=True;db.commit()
        ws.send_text('next')
        with pytest.raises(WebSocketDisconnect):ws.receive_json()


@pytest.mark.parametrize('cursor',['999999','invalid','-1'])
def test_invalid_cursor_resets_to_authoritative_snapshot(capture,cursor):
    app,client,headers,path,run=capture
    with client.websocket_connect(path+'/updates?after='+cursor,headers={'origin':ORIGIN}) as ws:
        reset=ws.receive_json()
        assert reset['kind']=='snapshot_required'
        assert reset['cursor']==client.get(path+'/snapshot').json()['update_cursor']


def test_pruned_cursor_and_repeat_delivery(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,count=1440000)
    with app.state.sessions() as db:
        db.execute(delete(LectureUpdate).where(LectureUpdate.sequence==2));db.commit()
    with client.websocket_connect(path+'/updates?after=1',headers={'origin':ORIGIN}) as ws:
        assert ws.receive_json()['kind']=='snapshot_required'
    for _ in range(2):
        with client.websocket_connect(path+'/updates?after=2',headers={'origin':ORIGIN}) as ws:
            assert ws.receive_json()['events'][0]['sequence']==3


def test_custom_detail_layout_roundtrip_prompt_and_limit(notes):
    app,client,headers,path,_=notes
    body={'expected_version':1,'model':'qwen3:4b','detail_prompt':'Explain mechanisms for a beginner.',
        'layout_prompt':'Start each topic with a timeline, then causes and consequences.'}
    response=client.post(path+'/notes/model',headers={**headers,'idempotency-key':str(uuid4())},json=body)
    assert response.status_code==200
    profile=client.get(path+'/notes').json()['profile']
    assert profile['detail_prompt']==body['detail_prompt'] and profile['layout_prompt']==body['layout_prompt']
    prompt=draft_messages({'profile':profile,'sources':[]})[-1]['content']
    assert body['detail_prompt'] in prompt and body['layout_prompt'] in prompt
    assert 'Organize the notes under descriptive topic headings.' not in prompt
    assert client.post(path+'/notes/model',headers={**headers,'idempotency-key':str(uuid4())},
        json={**body,'expected_version':2,'detail_prompt':'x'*2001}).status_code==422
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
    assert client.get(path+'/notes').json()['revision']['profile']==profile


def test_running_notes_finish_on_appends_then_coalesce_followup(capture):
    app,client,headers,path,run=capture
    enable(app,client,headers,path);append(*capture,0);plan(app.state.sessions)
    def during_inference():
        assert upload(client,headers,path,run,1,count=1440000).status_code==200
        plan_pending(app.state.sessions);plan(app.state.sessions)
        with app.state.sessions() as db:
            assert db.scalar(select(func.count()).select_from(NoteRequest))==1
        assert client.get(path+'/notes').json()['status']=='generating'
    assert execute(app.state.sessions,FakeNotes(after=during_inference),claim(app.state.sessions),heartbeat=False)
    assert client.get(path+'/notes').json()['stale']
    finish_all(app);plan(app.state.sessions)
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
    assert not client.get(path+'/notes').json()['stale']


def test_declared_gap_fences_notes_before_reconciler_runs(capture):
    app,client,headers,path,run=capture
    enable(app,client,headers,path);append(*capture,0);plan(app.state.sessions)
    def during_inference():
        response=seal(client,headers,path,run,samples=1440000,
            gaps=[{'reason':'microphone_lost','after_sample':720000,'unknown_extent':True}])
        assert response.status_code==200
    assert not execute(app.state.sessions,FakeNotes(after=during_inference),claim(app.state.sessions),heartbeat=False)
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(NoteRevision))==0


def test_replay_pages_are_ordered_and_bounded(capture):
    from notetaker.models import Lecture
    app,client,headers,path,run=capture
    with app.state.sessions() as db:
        lecture=db.get(Lecture,path.split('/')[-1])
        for _ in range(205):
            lecture.update_seq+=1
            db.add(LectureUpdate(lecture_id=lecture.id,sequence=lecture.update_seq,kind='test.changed',entity_id=run['id'],entity_version=1))
        db.commit()
    with client.websocket_connect(path+'/updates?after=0',headers={'origin':ORIGIN}) as ws:
        batches=[ws.receive_json() for _ in range(3)]
        events=[e for batch in batches for e in batch['events']]
        assert [len(batch['events']) for batch in batches]==[100,100,7]
        assert [e['sequence'] for e in events]==list(range(1,208))


def test_seal_during_live_inference_cannot_skip_unplanned_tail(capture):
    app,client,headers,path,run=capture
    upload(client,headers,path,run,count=1440000);plan_pending(app.state.sessions)
    chosen=speech_claim(app.state.sessions)
    seal(client,headers,path,run,samples=1440000)
    assert speech_execute(app.state.sessions,app.state.audio_store,FakeSpeech(),chosen,heartbeat=False)
    plan_pending(app.state.sessions);finish_all(app)
    assert client.get(path+'/transcript').json()['processing_delay_seconds']==0
    assert client.get(path+'/transcript').json()['counts']['completed']==2


def test_gap_replanning_preserves_later_cores_without_overlap(capture):
    from notetaker.transcription import windows_for
    from notetaker.models import Lecture
    app,client,headers,path,run=capture
    for sequence in range(3):append(*capture,sequence)
    original=client.get(path+'/transcript').json()['snapshot']['segments']
    seal(client,headers,path,run,last=2,samples=4320000,
        gaps=[{'reason':'microphone_lost','after_sample':480000,'unknown_extent':True}])
    plan_pending(app.state.sessions);finish_all(app)
    with app.state.sessions() as db:
        windows=windows_for(db,db.get(Lecture,path.split('/')[-1]))
        assert [(w.core_start//48000,w.core_end//48000) for w,_,_ in windows]==[(0,10),(10,24),(24,48),(48,72),(72,90)]
    final=client.get(path+'/transcript').json()['snapshot']['segments']
    assert {p['id'] for p in original[1:]} <= {p['id'] for p in final}
