"""Synthetic-only end-to-end speech probe against the running local app and worker.

Creates clearly named synthetic course/lecture records for browser review. A temporary
owner session is revoked afterwards. Never reads a microphone or uploads to a remote API.
"""
import argparse
import hashlib
import io
import json
import re
import secrets
import time
import wave
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
import httpx
from sqlalchemy import select
from .config import Settings
from .db import database
from .models import Owner, Session, SpeechGeneration, now
from .security import digest


def words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?",text.lower())


def word_error(reference,hypothesis):
    left,right=words(reference),words(hypothesis)
    costs=list(range(len(right)+1))
    for i,a in enumerate(left,1):
        current=[i]
        for j,b in enumerate(right,1):
            current.append(min(current[-1]+1,costs[j]+1,costs[j-1]+(a!=b)))
        costs=current
    return {'reference_words':len(left),'recognized_words':len(right),'edit_distance':costs[-1],
        'wer':costs[-1]/len(left) if left else None}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audio',type=Path,required=True)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--title',default='Synthetic CS speech — no microphone')
    args=parser.parse_args()
    settings=Settings()
    if settings.preview:raise SystemExit('Use the PostgreSQL application.')
    engine,sessions=database(settings.database_url)
    with wave.open(str(args.audio),'rb') as wav:
        if wav.getnchannels()!=1 or wav.getsampwidth()!=2:raise SystemExit('Expected synthetic mono PCM16 WAV.')
        rate=wav.getframerate();pcm=wav.readframes(wav.getnframes());samples=len(pcm)//2
    token=secrets.token_urlsafe(48);csrf=digest('csrf:'+token)
    with sessions() as db:
        owner=db.scalar(select(Owner))
        if not owner:raise SystemExit('Unlock the workspace once first.')
        db.add(Session(token_hash=digest(token),owner_id=owner.id,csrf_hash=digest(csrf),expires_at=now()+timedelta(hours=1)))
        db.commit()
    try:
        with httpx.Client(base_url='http://127.0.0.1:8010',cookies={'nt_session':token},timeout=30) as client:
            headers={'Origin':settings.web_origin,'X-CSRF-Token':csrf}
            def post(path,body):
                response=client.post(path,json=body,headers={**headers,'Idempotency-Key':str(uuid4())})
                response.raise_for_status();return response.json()
            course=post('/courses',{'name':'Transcription checks (synthetic)','code':'M03 TEST'})
            lecture=post('/courses/'+course['id']+'/lectures',{'title':args.title})
            path='/lectures/'+lecture['id'];grant=secrets.token_urlsafe(48)
            run=post(path+'/capture-runs',{'grant':grant,'sample_rate':rate,'expected_capture_epoch':0})
            sequence=0
            for start in range(0,samples,2*rate):
                count=min(2*rate,samples-start);buffer=io.BytesIO()
                with wave.open(buffer,'wb') as wav:
                    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm[start*2:(start+count)*2])
                raw=buffer.getvalue()
                identity={'run_id':run['id'],'capture_epoch':run['capture_epoch'],'sequence':sequence,
                    'start_sample':start,'sample_count':count,'sample_rate':rate,'channels':1,'encoding':'pcm_s16le_wav',
                    'sha256':hashlib.sha256(raw).hexdigest(),'byte_length':len(raw)}
                response=client.put(path+'/capture-runs/'+run['id']+'/chunks/'+str(sequence),content=raw,
                    headers={**headers,'X-Capture-Grant':grant,'X-Chunk-Identity':json.dumps(identity),'Content-Type':'audio/wav'})
                response.raise_for_status()
                assert response.json()['sha256']==identity['sha256']
                response=client.post(path+'/capture-runs/'+run['id']+'/heartbeat',json={},
                    headers={**headers,'X-Capture-Grant':grant});response.raise_for_status()
                sequence+=1
            manifest=client.get(path+'/capture-runs/'+run['id']+'/manifest').json()
            response=client.post(path+'/capture-runs/'+run['id']+'/seal',json={'expected_version':manifest['manifest_version'],
                'last_sequence':sequence-1,'final_sample_count':samples,'gaps':[]},headers={**headers,'X-Capture-Grant':grant})
            response.raise_for_status()
            started=time.monotonic();data=None
            while time.monotonic()-started<600:
                response=client.get(path+'/transcript');response.raise_for_status();data=response.json()
                if data['status'] in ('processed','needs_attention'):break
                time.sleep(2)
            if not data or data['status']!='processed':
                raise RuntimeError('Synthetic transcription did not complete: '+str(data and data['status']))
            passages=data['snapshot']['segments'];hypothesis=' '.join(p['text'] for p in passages)
            playback=[]
            for passage in passages:
                response=client.get(passage['audio_url'].removeprefix('/api'));response.raise_for_status()
                with wave.open(io.BytesIO(response.content),'rb') as wav:
                    assert wav.getframerate()==rate
                    assert wav.getnframes()==passage['end_sample']-passage['start_sample']
                playback.append(passage['id'])
            with sessions() as db:
                generations=[g.metadata_json for g in db.scalars(select(SpeechGeneration).where(SpeechGeneration.lecture_id==lecture['id']))]
            report={'fixture':args.audio.name,'synthetic_only':True,'lecture_id':lecture['id'],
                'audio_sha256':hashlib.sha256(args.audio.read_bytes()).hexdigest(),'sample_rate':rate,'duration_seconds':samples/rate,
                'upload_chunks':sequence,'elapsed_after_seal_seconds':round(time.monotonic()-started,2),
                'transcript':hypothesis,'passages':passages,'issues':data['snapshot']['issues'],
                'playback_verified':len(playback),'generations':generations,
                'quality_scope':'Synthetic engineering baseline; not real-lecture or human-reviewed qualification.'}
            if args.reference:report['word_error']=word_error(args.reference.read_text(encoding='utf8'),hypothesis)
            args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2),encoding='utf8')
            print(json.dumps({k:report[k] for k in ('lecture_id','duration_seconds','elapsed_after_seal_seconds','playback_verified')}))
            print('Synthetic report written to',args.report)
    finally:
        with sessions() as db:
            session=db.get(Session,digest(token))
            if session:session.revoked=True;db.commit()
        engine.dispose()


if __name__=='__main__':main()

