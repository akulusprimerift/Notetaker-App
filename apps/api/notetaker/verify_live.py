"""Paced synthetic audio through the running app, real speech and note workers."""
import argparse
import hashlib
import io
import json
import secrets
import threading
import time
import wave
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
import httpx
from sqlalchemy import select
from .config import Settings
from .db import database
from .models import Owner, Session, now
from .security import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--report', type=Path, default=Path('.local/m06-live-model-check.json'))
    args = parser.parse_args()
    settings = Settings()
    if settings.preview: raise SystemExit('Use the running PostgreSQL app for this probe.')
    with wave.open(str(args.audio), 'rb') as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2: raise SystemExit('Expected synthetic mono PCM16 WAV.')
        rate = wav.getframerate()
        pcm = wav.readframes(min(wav.getnframes(), args.seconds * rate))
    samples = len(pcm)//2
    engine, sessions = database(settings.database_url)
    token = secrets.token_urlsafe(48); csrf = digest('csrf:' + token)
    with sessions() as db:
        owner = db.scalar(select(Owner))
        if not owner: raise SystemExit('Unlock the workspace once before running the probe.')
        db.add(Session(token_hash=digest(token), owner_id=owner.id, csrf_hash=digest(csrf), expires_at=now()+timedelta(hours=1)))
        db.commit()
    report = {'synthetic_only': True, 'microphone_access': False, 'duration_seconds': samples/rate,
        'audio_sha256': hashlib.sha256(pcm).hexdigest(), 'first_transcript_seconds': None,
        'first_preview_seconds': None, 'first_saved_notes_seconds': None, 'preview_updates': 0,
        'notes_before_seal': False, 'final_ready': False, 'release_eligible': False}
    stop = threading.Event(); watcher = None
    try:
        with httpx.Client(base_url='http://127.0.0.1:8010', cookies={'nt_session': token}, timeout=30, trust_env=False) as client:
            headers = {'Origin': settings.web_origin, 'X-CSRF-Token': csrf}
            def post(route, body):
                response = client.post(route, json=body, headers={**headers, 'Idempotency-Key': str(uuid4())})
                response.raise_for_status(); return response.json()
            models = client.get('/note-models').json()['models']
            if not models: raise RuntimeError('No supported installed local note model is available.')
            model = min(models, key=lambda m: m['size'])
            report['model'] = model['name']
            course = post('/courses', {'name': 'Live notes checks (synthetic)', 'code': 'M06 TEST'})
            lecture = post('/courses/'+course['id']+'/lectures', {'title': 'Synthetic live speech and streaming notes — no microphone'})
            report['lecture_id'] = lecture['id']; path = '/lectures/'+lecture['id']
            post(path+'/notes/model', {'expected_version': 0, 'model': model['name']})
            grant = secrets.token_urlsafe(48)
            run = post(path+'/capture-runs', {'grant': grant, 'sample_rate': rate, 'expected_capture_epoch': 0})
            started = time.monotonic()
            def elapsed(): return round(time.monotonic()-started, 2)
            def watch():
                try:
                    with httpx.stream('GET', 'http://127.0.0.1:3000/api'+path+'/notes/stream',
                            cookies={'nt_session': token}, timeout=15, trust_env=False) as response:
                        response.raise_for_status()
                        report['stream_encoding'] = response.headers.get('content-encoding', 'none')
                        for line in response.iter_lines():
                            if stop.is_set(): break
                            if not line.startswith('data: '): continue
                            data = json.loads(line[6:])
                            if data.get('text'):
                                report['preview_updates'] += 1
                                if report['first_preview_seconds'] is None:
                                    report['first_preview_seconds'] = elapsed()
                                    print('First model text reached the app at', elapsed(), 'seconds.', flush=True)
                except Exception as exc:
                    report['stream_error'] = type(exc).__name__
            watcher = threading.Thread(target=watch, daemon=True); watcher.start()
            def inspect():
                transcript = client.get(path+'/transcript').json()
                notes = client.get(path+'/notes').json()
                if (transcript.get('snapshot') or {}).get('segments'):
                    if report['first_transcript_seconds'] is None:
                        report['first_transcript_seconds'] = elapsed()
                        print('First transcript appeared at', elapsed(), 'seconds while recording.', flush=True)
                if notes.get('revision') and report['first_saved_notes_seconds'] is None:
                    report['first_saved_notes_seconds'] = elapsed()
                return transcript, notes
            sequence = uploaded = 0
            print('Testing real local models with paced synthetic audio:', model['name'], flush=True)
            try:
                for start in range(0, samples, 2*rate):
                    count = min(2*rate, samples-start)
                    # Save each synthetic chunk at the time a real capture would have it.
                    time.sleep(max(0, (start+count)/rate-(time.monotonic()-started)))
                    buffer = io.BytesIO()
                    with wave.open(buffer, 'wb') as wav:
                        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(pcm[start*2:(start+count)*2])
                    raw = buffer.getvalue()
                    identity = {'run_id': run['id'], 'capture_epoch': run['capture_epoch'], 'sequence': sequence,
                        'start_sample': start, 'sample_count': count, 'sample_rate': rate, 'channels': 1,
                        'encoding': 'pcm_s16le_wav', 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw)}
                    response = client.put(path+'/capture-runs/'+run['id']+'/chunks/'+str(sequence), content=raw,
                        headers={**headers, 'X-Capture-Grant': grant, 'X-Chunk-Identity': json.dumps(identity), 'Content-Type': 'audio/wav'})
                    response.raise_for_status(); sequence += 1; uploaded += count
                    response = client.post(path+'/capture-runs/'+run['id']+'/heartbeat', json={}, headers={**headers, 'X-Capture-Grant': grant})
                    response.raise_for_status()
                    transcript, notes = inspect()
                    if notes.get('revision'): report['notes_before_seal'] = True
                # Keep the synthetic run open briefly to measure note progress independently of sealing.
                while elapsed() < min(args.timeout, 120) and not report['notes_before_seal']:
                    transcript, notes = inspect()
                    if notes.get('revision'): report['notes_before_seal'] = True; break
                    if notes['status'] == 'needs_attention': break
                    response = client.post(path+'/capture-runs/'+run['id']+'/heartbeat', json={}, headers={**headers, 'X-Capture-Grant': grant})
                    response.raise_for_status(); time.sleep(2)
            finally:
                manifest = client.get(path+'/capture-runs/'+run['id']+'/manifest').json()
                response = client.post(path+'/capture-runs/'+run['id']+'/seal', json={'expected_version': manifest['manifest_version'],
                    'last_sequence': sequence-1, 'final_sample_count': uploaded, 'gaps': []}, headers={**headers, 'X-Capture-Grant': grant})
                response.raise_for_status(); report['sealed_at_seconds'] = elapsed()
            while elapsed() < args.timeout:
                transcript, notes = inspect()
                if transcript['status'] == 'processed' and notes['status'] == 'ready' and not notes['stale']:
                    report['final_ready'] = True; break
                if transcript['status'] == 'needs_attention' or notes['status'] == 'needs_attention': break
                time.sleep(2)
            report.update(elapsed_seconds=elapsed(), transcript_status=transcript['status'], note_status=notes['status'],
                note_error=notes.get('error_code'), source_count=len((transcript.get('snapshot') or {}).get('segments', [])))
            if notes.get('revision'):
                revision = notes['revision']
                response = client.get(path+'/notes/revisions/'+revision['id']+'/export'); response.raise_for_status()
                report.update(revision_id=revision['id'], exported_bytes=len(response.content), metadata=revision['metadata'])
    finally:
        stop.set()
        if watcher: watcher.join(timeout=3)
        with sessions() as db:
            session = db.get(Session, digest(token))
            if session: session.revoked = True; db.commit()
        engine.dispose()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('metadata', 'audio_sha256')}, indent=2), flush=True)
    return 0 if report['final_ready'] and report['notes_before_seal'] and report['first_preview_seconds'] is not None else 1


if __name__ == '__main__': raise SystemExit(main())
