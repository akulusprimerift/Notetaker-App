"""Isolated real-service synthetic smoke. Does not open the student library."""
import argparse
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('resources', type=Path)
    parser.add_argument('--source-host', action='store_true')
    args = parser.parse_args()
    profile = Path('.local') / ('host-smoke-' + uuid4().hex)
    profile.mkdir(parents=True)
    config = {'resources': str(args.resources.resolve()), 'data': str(profile.resolve()),
        'secret': secrets.token_hex(32), 'speechPath': ''}
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
