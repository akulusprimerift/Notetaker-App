"""Isolated real-service synthetic smoke. Does not open the student library."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time
import wave
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('resources', type=Path)
    parser.add_argument('--source-host', action='store_true')
    parser.add_argument('--speech-model', type=Path)
    parser.add_argument('--synthetic-audio', type=Path)
    parser.add_argument('--note-model')
    args = parser.parse_args()
    profile = Path('.local') / ('host-smoke-' + uuid4().hex)
    profile.mkdir(parents=True)
    config = {'resources': str(args.resources.resolve()), 'data': str(profile.resolve()),
        'secret': secrets.token_hex(32), 'speechPath': str(args.speech_model.resolve()) if args.speech_model else ''}
    executable = [sys.executable, str(Path('apps/api/windows_service.py').resolve())] if args.source_host else [str(args.resources.resolve() / 'service/NotetakerService.exe')]
    child = subprocess.Popen([*executable, 'host'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW, env=os.environ.copy())
    messages = queue.Queue()
    def read(stream):
        for line in stream:
            messages.put(line)
    threading.Thread(target=read, args=(child.stdout,), daemon=True).start()
    threading.Thread(target=read, args=(child.stderr,), daemon=True).start()
    try:
        child.stdin.write(json.dumps(config) + '\n')
        child.stdin.flush()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f'Host stopped: {child.returncode}; inspect {profile}')
            try:
                line = messages.get(timeout=1)
            except queue.Empty:
                continue
            print(line.strip(), flush=True)
            value = json.loads(line)
            if value.get('status') == 'failed':
                raise RuntimeError(value['message'])
            if value.get('status') == 'ready':
                break
        else:
            raise RuntimeError('Startup deadline expired')
        with httpx.Client(base_url='http://127.0.0.1:8010', timeout=10) as client:
            response = client.post('/session/open', headers={'origin': 'http://127.0.0.1:3000'})
            response.raise_for_status()
            headers = {'origin': 'http://127.0.0.1:3000', 'x-csrf-token': response.json()['csrf_token'], 'idempotency-key': str(uuid4())}
            response = client.post('/courses', json={'name': 'Synthetic standalone service smoke', 'code': 'TEST'}, headers=headers)
            response.raise_for_status()
            assert client.get('/courses').json()[0]['name'] == 'Synthetic standalone service smoke'
            if args.synthetic_audio:
                assert args.speech_model and args.note_model, 'Select both existing local models for the live probe'
                course = response.json()
                def post(path, body, extra=None):
                    result = client.post(path, json=body, headers={**headers,
                        'idempotency-key': str(uuid4()), **(extra or {})})
                    result.raise_for_status()
                    return result.json()
                lecture = post('/courses/'+course['id']+'/lectures', {'title':'Synthetic live inference — no microphone'})
                path = '/lectures/'+lecture['id']
                post(path+'/notes/model', {'expected_version':0, 'model':args.note_model})
                with wave.open(str(args.synthetic_audio), 'rb') as audio:
                    assert audio.getnchannels()==1 and audio.getsampwidth()==2
                    rate=audio.getframerate(); pcm=audio.readframes(audio.getnframes())
                grant=secrets.token_urlsafe(48)
                run=post(path+'/capture-runs', {'grant':grant,'sample_rate':rate,'expected_capture_epoch':0})
                for sequence,start in enumerate(range(0,len(pcm)//2,2*rate)):
                    frames=pcm[start*2:(start+2*rate)*2]; buffer=io.BytesIO()
                    with wave.open(buffer,'wb') as audio:
                        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(frames)
                    raw=buffer.getvalue()
                    identity={'run_id':run['id'],'capture_epoch':run['capture_epoch'],'sequence':sequence,
                        'start_sample':start,'sample_count':len(frames)//2,'sample_rate':rate,'channels':1,
                        'encoding':'pcm_s16le_wav','sha256':hashlib.sha256(raw).hexdigest(),'byte_length':len(raw)}
                    result=client.put(path+'/capture-runs/'+run['id']+'/chunks/'+str(sequence),content=raw,
                        headers={**headers,'X-Capture-Grant':grant,'X-Chunk-Identity':json.dumps(identity),'Content-Type':'audio/wav'})
                    result.raise_for_status()
                # Deliberately leave capture unsealed: final-only processing cannot pass.
                deadline=time.monotonic()+600
                while time.monotonic()<deadline:
                    transcript=client.get(path+'/transcript').json()
                    notes=client.get(path+'/notes').json()
                    if (transcript.get('snapshot') or {}).get('segments') and notes.get('revision'):
                        assert transcript['mode']=='live'
                        print(json.dumps({'live_transcript':'passed','live_notes':'passed',
                            'passages':len(transcript['snapshot']['segments'])}),flush=True)
                        break
                    if transcript['errors'] or notes.get('error_code'):
                        raise RuntimeError(f"Inference failure: {transcript['errors']}, {notes.get('error_code')}")
                    time.sleep(1)
                else:
                    raise RuntimeError('Live inference deadline expired')
        print(json.dumps({'host': 'passed', 'postgres_api_write_read': 'passed', 'profile': str(profile)}), flush=True)
    finally:
        child.stdin.close()
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)


if __name__ == '__main__':
    main()
