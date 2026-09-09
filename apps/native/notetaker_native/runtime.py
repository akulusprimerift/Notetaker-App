"""Private per-user services; no Docker, shell or installed Python dependency."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from .process_job import ProcessJob


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[3]))


def command(mode, *args):
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).with_name('NotetakerService.exe')), mode, *args]
    return [sys.executable, str(resource_root()/'apps/native/service.py'), mode, *args]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def model_locations():
    """Only inspect conventional local locations; never download model weights."""
    home = Path.home()
    roots = [home/'.ollama/models', home/'.cache/lm-studio/models', home/'.lmstudio/models']
    if os.environ.get('OLLAMA_MODELS'):
        roots.insert(0, Path(os.environ['OLLAMA_MODELS']))
    speech = [resource_root()/'.local/models', home/'.cache/huggingface/hub']
    return {'ollama': [str(p) for p in roots if (p/'manifests').is_dir()],
            'gguf': [str(p) for root in roots if root.is_dir() for p in root.glob('*/*/*.gguf')],
            'speech': [str(p.parent) for root in speech if root.is_dir() for p in root.glob('**/model.bin')
                       if (p.parent/'config.json').is_file()]}


class Runtime:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.processes = []
        self.job = ProcessJob()
        self.logs = []
        self.port = free_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self.ollama_port = free_port()
        self.config_path = self.directory/'settings.json'
        self.config = json.loads(self.config_path.read_text('utf-8')) if self.config_path.exists() else {}
        self.detected = model_locations()
        # Use an already-installed local model store by default. The previous
        # behavior created an empty per-library store even when Ollama models
        # were present in the user's normal location.
        if not self.config.get('ollama_models') and self.detected['ollama']:
            self.config['ollama_models'] = self.detected['ollama'][0]
        if not self.config.get('speech_model') and self.detected['speech']:
            self.config['speech_model'] = self.detected['speech'][0]

    def save_config(self):
        temporary = self.config_path.with_suffix('.pending')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(self.config, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.config_path)

    def spawn(self, args, name, env):
        log = (self.directory/(name+'.log')).open('ab')
        self.logs.append(log)
        process = subprocess.Popen(args, env=env, cwd=self.directory, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.processes.append(process)
        self.job.assign(process)
        return process

    def start(self):
        env = os.environ.copy()
        env.update(NOTETAKER_STANDALONE='true', NOTETAKER_PREVIEW='false',
                   NOTETAKER_DATABASE_URL='sqlite:///'+(self.directory/'workspace.db').as_posix(),
                   NOTETAKER_AUDIO_DIRECTORY=str(self.directory/'audio'), NOTETAKER_WEB_ORIGIN=self.url,
                   NOTETAKER_OLLAMA_URL=f'http://127.0.0.1:{self.ollama_port}',
                   NOTETAKER_SPEECH_MODEL_PATH=self.config.get('speech_model', ''),
                   PYTHONPATH=os.pathsep.join([str(resource_root()/'apps/api'), str(resource_root()/'apps/native')]))
        self.env = env
        migrate = self.spawn(command('migrate'), 'migration', env)
        if migrate.wait(timeout=90):
            raise RuntimeError('The library upgrade failed. Your library is preserved; see migration.log.')
        ollama = resource_root()/'vendor/ollama/ollama.exe'
        if not ollama.exists():
            ollama = resource_root()/'.local/native-vendor/ollama/ollama.exe'
        if not ollama.exists():
            raise RuntimeError('The bundled note runtime is missing. Reinstall the complete application folder.')
        self.ollama = ollama
        model_env = {**env, 'OLLAMA_HOST':f'127.0.0.1:{self.ollama_port}', 'OLLAMA_NO_CLOUD':'1', 'OLLAMA_NOPRUNE':'1',
                     'OLLAMA_MODELS':self.config.get('ollama_models', str(self.directory/'models'))}
        self.model_env = model_env
        self.spawn([str(ollama), 'serve'], 'models', model_env)
        self.spawn(command('api', str(self.port)), 'api', env)
        deadline = time.monotonic()+60
        while time.monotonic() < deadline:
            try:
                if httpx.get(self.url+'/health', timeout=1, trust_env=False).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.2)
        else:
            raise RuntimeError('The local library service did not start. See api.log in the library folder.')
        self.spawn(command('notes'), 'notes', env)
        self.spawn(command('speech'), 'speech', env)

    def close(self):
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
        for process in self.processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in self.logs:
            log.close()
        self.job.close()
        self.processes.clear()
        self.logs.clear()
