"""Verify bundled CPU inference using explicitly provided, already-local weights."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--speech', type=Path, required=True)
    parser.add_argument('--ollama-models', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
    env = {**os.environ, 'OLLAMA_HOST':f'127.0.0.1:{port}', 'OLLAMA_MODELS':str(args.ollama_models.resolve()),
           'OLLAMA_NO_CLOUD':'1', 'OLLAMA_NOPRUNE':'1'}
    executable = args.bundle/'_internal/vendor/ollama/ollama.exe'
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.with_suffix('.log').open('wb') as log:
        process = subprocess.Popen([str(executable),'serve'],env=env,stdout=log,stderr=log,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        from notetaker_native.process_job import ProcessJob
        job = ProcessJob(); job.assign(process)
        try:
            url = f'http://127.0.0.1:{port}'
            with httpx.Client(base_url=url,trust_env=False,timeout=300) as client:
                deadline = time.monotonic()+30
                while True:
                    try:
                        response = client.get('/api/tags'); response.raise_for_status(); break
                    except httpx.HTTPError:
                        if time.monotonic()>deadline: raise
                        time.sleep(.2)
                models = [m for m in response.json()['models'] if m.get('details',{}).get('family') in ('qwen2','qwen3') and not m.get('remote_model')]
                if not models: raise RuntimeError('No compatible local Qwen model found')
                model = min(models,key=lambda m:m['size'])['name']
                response = client.post('/api/chat',json={'model':model,'stream':False,'think':False,
                    'messages':[{'role':'user','content':'Reply with the word ready.'}],
                    'options':{'num_predict':8,'num_ctx':2048}})
                response.raise_for_status(); result = response.json()
                if not result.get('message',{}).get('content'): raise RuntimeError('Bundled note runtime returned no text')
            speech = subprocess.run([str(args.bundle/'NotetakerService.exe'),'verify-speech',str(args.speech.resolve())],
                                    capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if speech.returncode: raise RuntimeError(speech.stderr.decode(errors='replace'))
            speech_result = json.loads(speech.stdout)
            if speech_result['outcome'] != 'silence': raise RuntimeError('Synthetic silence was misclassified')
            report = {'bundled_note_runtime':True,'model':model,'response':result['message']['content'],
                      'bundled_speech_runtime':True,'synthetic_speech_probe':speech_result,
                      'model_downloads':False,'microphone_accessed':False}
            args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2))
        finally:
            job.close(); process.wait(timeout=10)


if __name__ == '__main__':
    main()
