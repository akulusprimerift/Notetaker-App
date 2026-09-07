"""Single local speech process; Kafka delivery and database recovery share fenced claims."""
import argparse
import json
import logging
import threading
import time
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, update
from .config import Settings
from .db import database
from .audio_store import AudioStore
from .models import (Lecture, Job, Outbox, Inbox, SpeechWindow, SpeechGeneration, CaptureRun,
    TranscriptSegment, TranscriptVersion, UploadReservation, now)
from .transcription import lock_lecture, schedule, read_audio, freeze_transcript, windows_for
from .speech_provider import WhisperProvider, SpeechFailure, validate_result

LEASE_SECONDS=60
TOPIC='notetaker.speech.v1'
log=logging.getLogger('notetaker.speech')


def plan_pending(sessions):
    with sessions() as db:
        ids=db.scalars(select(Job.lecture_id).where(Job.kind=='speech.chunk',Job.status=='due').distinct()).all()
    for lecture_id in ids:
        with sessions() as db:
            lecture=lock_lecture(db,lecture_id)
            if lecture and not lecture.tombstoned:
                schedule(db,lecture)
            db.commit()


def claim(sessions, job_id=None):
    with sessions() as db:
        query=select(Job.id,Job.lecture_id).where(Job.kind=='speech.window',
            ((Job.status=='due') & (Job.due_at<=now())) | ((Job.status=='running') & (Job.lease_expires_at<=now())))
        if job_id: query=query.where(Job.id==job_id)
        candidates=db.execute(query.order_by(Job.due_at,Job.id).limit(50)).all()
    for candidate, lecture_id in candidates:
        with sessions() as db:
            lecture=lock_lecture(db,lecture_id)
            job=db.get(Job,candidate)
            if not job or not (job.status=='due' and job.due_at<=now() or job.status=='running' and job.lease_expires_at<=now()):
                continue
            window=db.get(SpeechWindow,job.input_revision)
            run=db.get(CaptureRun,window.run_id)
            if (lecture.tombstoned or job.lifecycle_epoch!=lecture.lifecycle_epoch or job.audio_epoch!=lecture.audio_epoch
                or run.manifest_version!=window.manifest_version):
                job.status='cancelled'; job.error_code='source_changed'; db.commit(); continue
            other=db.scalar(select(Job.id).where(Job.lecture_id==lecture_id,Job.kind=='speech.window',
                Job.id!=job.id,Job.status=='running',Job.lease_expires_at>now()).limit(1))
            if other: continue
            job.status='running'; job.attempt_token=str(uuid4()); job.lease_expires_at=now()+timedelta(seconds=LEASE_SECONDS)
            job.attempts+=1; job.error_code=None
            db.commit()
            return job.id,job.attempt_token
    return None


def live_attempt(db, job_id, token):
    lecture_id=db.scalar(select(Job.lecture_id).where(Job.id==job_id))
    if not lecture_id:return None
    lecture=lock_lecture(db,lecture_id)
    job=db.get(Job,job_id)
    window=db.get(SpeechWindow,job.input_revision)
    run=db.get(CaptureRun,window.run_id)
    if (job.status!='running' or job.attempt_token!=token or job.lease_expires_at<=now()
        or lecture.tombstoned or lecture.lifecycle_epoch!=job.lifecycle_epoch or lecture.audio_epoch!=job.audio_epoch
        or run.manifest_version!=window.manifest_version):
        return None
    return lecture,job,window,run


def renew(sessions, job_id, token):
    with sessions() as db:
        active=live_attempt(db,job_id,token)
        if not active:return False
        active[1].lease_expires_at=now()+timedelta(seconds=LEASE_SECONDS); db.commit(); return True


def publish(sessions, job_id, token, result):
    with sessions() as db:
        active=live_attempt(db,job_id,token)
        if not active:return False
        lecture,job,window,run=active
        validate_result(result,window)
        generation=SpeechGeneration(lecture_id=lecture.id,window_id=window.id,attempt_token=token,metadata_json=result['metadata'])
        db.add(generation);db.flush()
        for position, data in enumerate(result['segments']):
            # A result never rewrites any previously published source or human correction.
            if db.scalar(select(TranscriptSegment.id).where(TranscriptSegment.window_id==window.id,TranscriptSegment.position==position)):
                continue
            segment=TranscriptSegment(lecture_id=lecture.id,window_id=window.id,position=position)
            db.add(segment);db.flush()
            db.add(TranscriptVersion(lecture_id=lecture.id,segment_id=segment.id,revision=1,
                author='machine',generation_id=generation.id,**data))
        window.outcome=result['outcome'];job.status='completed';job.lease_expires_at=None;job.error_code=None
        db.flush()
        # Original chunk jobs complete only when all current inference windows for their run complete.
        run_jobs=[j for w,j,_ in windows_for(db,lecture) if w.run_id==run.id]
        if run_jobs and all(j.status=='completed' for j in run_jobs):
            chunk_ids=db.scalars(select(UploadReservation.id).where(UploadReservation.run_id==run.id)).all()
            db.execute(update(Job).where(Job.kind=='speech.chunk',Job.input_revision.in_(chunk_ids),
                Job.lecture_id==lecture.id).values(status='completed'))
        freeze_transcript(db,lecture);db.commit();return True


def fail(sessions, job_id, token, failure):
    with sessions() as db:
        active=live_attempt(db,job_id,token)
        if not active:return
        lecture,job,_,_=active
        job.error_code=failure.code;job.lease_expires_at=None
        job.status='due' if failure.retryable and (job.attempts<5 or failure.code=='model_unavailable') else 'failed'
        delay=60 if failure.code=='model_unavailable' else min(60,2**min(job.attempts,6))
        job.due_at=now()+timedelta(seconds=delay)
        freeze_transcript(db,lecture);db.commit()


def execute(sessions, store, provider, claimed, heartbeat=True):
    job_id,token=claimed
    stop=threading.Event()
    def beat():
        while not stop.wait(10):
            try:
                if not renew(sessions,job_id,token): return
            except Exception:
                log.warning('speech_lease_renewal_failed job_id=%s',job_id)
    thread=threading.Thread(target=beat,daemon=True)
    if heartbeat:thread.start()
    try:
        with sessions() as db:
            job=db.get(Job,job_id);window=db.get(SpeechWindow,job.input_revision);run=db.get(CaptureRun,window.run_id)
            db.expunge(window);db.expunge(run)
        with sessions() as db:
            try: audio=read_audio(db,store,run,window.context_start,window.context_end)
            except Exception as exc: raise SpeechFailure('audio_integrity_unavailable') from exc
        result=provider.transcribe(audio,window,run.sample_rate)
        return publish(sessions,job_id,token,result)
    except SpeechFailure as exc:
        fail(sessions,job_id,token,exc);return False
    except Exception:
        fail(sessions,job_id,token,SpeechFailure('speech_worker_failed'));return False
    finally:
        stop.set()
        if heartbeat:thread.join(timeout=2)


def event_payload(event):
    return {'schema_version':1,'event_id':event.id,'lecture_id':event.lecture_id,
        'entity_id':event.entity_id,'lifecycle_epoch':event.lifecycle_epoch,'event_type':event.event_type}


def dispatch(sessions, producer):
    with sessions() as db:
        events=db.scalars(select(Outbox).where(Outbox.published_at.is_(None),
            Outbox.event_type.in_(['audio.verified','speech.requested'])).order_by(Outbox.created_at).limit(25)).all()
        for event in events:db.expunge(event)
    for event in events:
        outcome=[]
        producer.produce(TOPIC,key=event.lecture_id,value=json.dumps(event_payload(event)).encode(),
            on_delivery=lambda err,msg:outcome.append(err))
        producer.flush(2)
        if not outcome or outcome[0] is not None:return False
        with sessions() as db:
            db.execute(update(Outbox).where(Outbox.id==event.id,Outbox.published_at.is_(None)).values(published_at=now()))
            db.commit()
    return True


def consume_event(sessions, payload):
    # Broker content is only a hint. Match the original private outbox record before accepting it.
    if not isinstance(payload,dict) or set(payload)!={'schema_version','event_id','lecture_id','entity_id','lifecycle_epoch','event_type'}:
        return None
    with sessions() as db:
        event=db.get(Outbox,payload.get('event_id'))
        if not event or payload!=event_payload(event):return None
        lecture=lock_lecture(db,event.lecture_id)
        if lecture.tombstoned or lecture.lifecycle_epoch!=event.lifecycle_epoch:return None
        existing=db.get(Inbox,('speech-v1',event.id))
        if not existing:
            db.add(Inbox(consumer='speech-v1',event_id=event.id));db.commit()
        job=db.get(Job,event.entity_id)
        return job.id if job and job.kind=='speech.window' else None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--once',action='store_true',help='Plan and execute at most one due window without Kafka.')
    args=parser.parse_args()
    settings=Settings()
    if settings.preview:raise SystemExit('Speech workers require PostgreSQL application storage.')
    engine,sessions=database(settings.database_url);store=AudioStore(settings);provider=WhisperProvider(settings)
    producer=consumer=None
    if not args.once:
        from confluent_kafka import Producer,Consumer
        producer=Producer({'bootstrap.servers':settings.kafka_bootstrap,'message.timeout.ms':2000,'log_level':0})
        consumer=Consumer({'bootstrap.servers':settings.kafka_bootstrap,'group.id':'notetaker-speech-v1',
            'enable.auto.commit':False,'auto.offset.reset':'earliest','log_level':0})
        consumer.subscribe([TOPIC])
    try:
        while True:
            plan_pending(sessions)
            hint=None
            if producer:
                try:
                    dispatch(sessions,producer)
                    message=consumer.poll(0.1)
                    if message and not message.error():
                        raw=message.value()
                        hint=consume_event(sessions,json.loads(raw)) if len(raw)<=2048 else None
                        consumer.commit(message=message,asynchronous=False)
                except Exception:
                    log.warning('speech_broker_unavailable') # Reconciliation below remains operational.
            claimed=claim(sessions,hint) if hint else None
            claimed=claimed or claim(sessions)
            if claimed:
                succeeded=execute(sessions,store,provider,claimed)
                log.info('speech_attempt job_id=%s published=%s',claimed[0],succeeded)
            if args.once:break
            if not claimed:time.sleep(2)
    finally:
        if consumer:consumer.close()
        engine.dispose()


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    main()

