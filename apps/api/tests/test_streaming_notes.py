import json
from types import SimpleNamespace
from datetime import timedelta
import pytest
from sqlalchemy import select
from test_workspace import setup
from test_capture import capture, upload
from test_transcription import speech, finish_all
from test_notes import notes, FakeNotes, valid, DIGEST, correction
from test_live import enable
from notetaker.note_batches import generate_batches, BATCH_SOURCES, BATCH_BYTES
from notetaker.note_provider import preview_text, OllamaNotes, NoteFailure
from notetaker.note_worker import plan, claim, execute, renew
from notetaker.speech_worker import plan_pending
from notetaker.models import NoteRequest, Job, NoteRevision, now
from notetaker.config import Settings


def test_six_second_cores_publish_before_seal_and_notes_wait_for_context(capture):
    app,client,headers,path,run=capture
    enable(app,client,headers,path)
    for sequence in range(4):
        assert upload(client,headers,path,run,sequence,count=96000).status_code==200
        plan_pending(app.state.sessions);finish_all(app);plan(app.state.sessions)
        if sequence<3: assert client.get(path+'/transcript').json()['snapshot'] is None
    transcript=client.get(path+'/transcript').json()
    assert transcript['snapshot']['segments'] and transcript['mode']=='live'
    assert claim(app.state.sessions) is None
    for sequence in range(4,13):
        assert upload(client,headers,path,run,sequence,count=96000).status_code==200
        plan_pending(app.state.sessions);finish_all(app);plan(app.state.sessions)
    chosen=claim(app.state.sessions)
    assert chosen and execute(app.state.sessions,FakeNotes(),chosen,heartbeat=False)
    assert client.get(path+'/notes').json()['revision']
    assert client.get(path+'/transcript').json()['mode']=='live'


def test_hour_plus_sources_are_bounded_and_appends_reuse_every_prior_source():
    evidence={'source_snapshot_id':'one','settings_version':1,'allow_ai_explanations':False,
        'profile':{'depth':'detailed','format':'topic_outline'},
        'sources':[{'id':str(i),'text':f'Concept {i}: '+'A lecture explanation. '*12,'start_ms':i*6000,'end_ms':(i+1)*6000} for i in range(750)]}
    class Counting(FakeNotes):
        seen=[]
        def generate(self, part, pref):
            self.seen.append(part)
            assert len(part['sources'])<=BATCH_SOURCES
            assert sum(len(s['text'].encode()) for s in part['sources'])<=BATCH_BYTES
            return super().generate(part,pref)
    provider=Counting();pref=SimpleNamespace(model='qwen3:4b',model_digest=DIGEST)
    output,metadata=generate_batches(provider,evidence,pref)
    assert len(output['coverage'])==750 and metadata['batch_count']>1
    assert [s['id'] for part in provider.seen for s in part['sources']]==[s['id'] for s in evidence['sources']]
    previous={'content':output,'metadata':metadata,'profile':evidence['profile']}
    newer={**evidence,'source_snapshot_id':'two','sources':[*evidence['sources'],{'id':'new','text':'The final qualification.'}]}
    provider.seen=[]
    appended,meta=generate_batches(provider,newer,pref,previous)
    assert meta['reused_sources']==750 and len(provider.seen)==1
    assert [s['id'] for s in provider.seen[0]['sources']]==['new']
    assert provider.seen[0]['preceding_context']
    assert appended['blocks'][:-1]==output['blocks']
    # A corrected source identity forces reconstruction and removes obsolete citations.
    fixed={**newer,'source_snapshot_id':'three','sources':[{**newer['sources'][0],'id':'corrected'},*newer['sources'][1:]]}
    output,meta=generate_batches(provider,fixed,pref,{'content':appended,'metadata':meta,'profile':evidence['profile']})
    assert meta['reused_sources']==0 and output['coverage'][0]['source_id']=='corrected'


def test_stream_preview_is_visible_before_save_and_failed_text_never_becomes_revision(notes):
    app,client,headers,path,_=notes
    class Streaming(FakeNotes):
        def generate_stream(self, evidence, pref, preview):
            preview('This is still being written…')
            with app.state.sessions() as db:
                request=db.scalar(select(NoteRequest))
                assert request.preview=='This is still being written…'
                assert (db.scalar(select(NoteRevision)) is not None) == self.corrupt
            assert client.get(path+'/notes').json()['status']=='generating'
            return self.generate(evidence,pref)
    assert execute(app.state.sessions,Streaming(),claim(app.state.sessions),heartbeat=False)
    saved=client.get(path+'/notes').json()['revision']
    correction(client,headers,path);plan(app.state.sessions)
    assert not execute(app.state.sessions,Streaming(corrupt=True),claim(app.state.sessions),heartbeat=False)
    assert client.get(path+'/notes').json()['revision']['id']==saved['id']
    assert client.get(path+'/notes').json()['error_code']=='invalid_output'


def test_reclaimed_attempt_clears_preview_and_fences_old_stream(notes):
    app,client,headers,path,_=notes
    old=claim(app.state.sessions)
    with app.state.sessions() as db:
        job=db.get(Job,old[0]);job.lease_expires_at=now()-timedelta(seconds=1)
        request=db.get(NoteRequest,job.input_revision);request.preview='Old partial output'
        db.commit()
    new=claim(app.state.sessions)
    with app.state.sessions() as db:
        request=db.get(NoteRequest,db.get(Job,new[0]).input_revision)
        assert request.preview=='' and request.preview_attempt==new[1]
    assert not renew(app.state.sessions,*old)
    assert execute(app.state.sessions,FakeNotes(),new,heartbeat=False)


def test_provider_decodes_partial_prose_without_showing_json_fields():
    raw='{"blocks":[{"topic":"A topic","passages":[{"text":"A line\\nwith \\"quotes\\" and \\u03b1","source_ids":["s1"]}]}]}'
    assert preview_text(raw)=='A topic\n\nA line\nwith "quotes" and α'
    assert preview_text('{"blocks":[{"topic":"Growing tit')=='Growing tit'
    assert preview_text('{"text":"line\\u03')=='line'
    assert preview_text('{"text":"line\\ud83d')=='line'


def test_ollama_ndjson_yields_prose_before_terminal_message(monkeypatch):
    observed=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_lines(self):
            yield json.dumps({'message':{'content':'{"blocks":[{"topic":"Growing'}})
            assert observed==['Growing']
            yield json.dumps({'message':{'content':' topic","passages":[{"text":"Visible prose"}]}]}'},'done':True,'done_reason':'stop'})
    class Client:
        def __init__(self,**kwargs):assert kwargs['trust_env'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def stream(self,method,route,json):
            assert json['stream'] is True
            return Response()
    monkeypatch.setattr('notetaker.note_provider.httpx.Client',Client)
    result=OllamaNotes(Settings()).stream_chat({},observed.append)
    assert result['done'] and observed[-1]=='Growing topic\n\nVisible prose'
