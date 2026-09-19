"""Owned Windows service tree for an explicitly separate PostgreSQL library."""
import ctypes
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time


def own_process_tree():
    """Windows closes the entire owned tree if this supervisor dies."""
    from ctypes import wintypes
    class Limits(ctypes.Structure):
        _fields_ = [('per_process', ctypes.c_int64), ('per_job', ctypes.c_int64),
            ('flags', wintypes.DWORD), ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t),
            ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
            ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ('read', 'write', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Limits), ('io', IO), ('process_memory', ctypes.c_size_t),
            ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    handle = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise RuntimeError('Cannot establish owned service lifetime')
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        raise RuntimeError('Cannot isolate owned service processes')
    return handle  # Deliberately retained until process exit.


def require_free_ports(ports):
    for port in ports:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                raise RuntimeError(f'Port {port} is in use. Close the other workspace before starting this library.') from None


def main(config):
    if sys.platform != 'win32':
        raise RuntimeError('This runtime is for Windows only')
    owned_job = own_process_tree()
    assert owned_job
    root = Path(config['resources']).resolve()
    data = Path(config['data']).resolve()
    data.mkdir(parents=True, exist_ok=True)
    account = os.environ['USERDOMAIN'] + '\\' + os.environ['USERNAME']
    subprocess.run(['icacls', str(data), '/inheritance:r', '/grant:r', account + ':(OI)(CI)F',
        '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    require_free_ports([3000, 8010, 55432, 19333, 29333, 18080, 28080, 18888, 28888, 18333, 28333, 11435])
    stop = threading.Event()
    def watch_parent():
        for _ in sys.stdin:
            stop.set()
            return
        stop.set()
    threading.Thread(target=watch_parent, daemon=True).start()
    env = {key: value for key, value in os.environ.items() if not key.startswith(('NOTETAKER_', 'PG', 'OLLAMA_', 'PYTHON'))}
    password = config['secret']
    env.update(NOTETAKER_DATABASE_URL=f'postgresql+psycopg://notetaker:{password}@127.0.0.1:55432/postgres',
        PYINSTALLER_RESET_ENVIRONMENT='1',
        NOTETAKER_PREVIEW='false', NOTETAKER_STANDALONE='false', NOTETAKER_BROKER_ENABLED='false',
        NOTETAKER_S3_ENDPOINT='http://127.0.0.1:18333', NOTETAKER_S3_ACCESS_KEY='notetaker',
        NOTETAKER_S3_SECRET_KEY=password, NOTETAKER_OLLAMA_URL='http://127.0.0.1:11435',
        NOTETAKER_WEB_ORIGIN='http://127.0.0.1:3000', NOTETAKER_SPEECH_MODEL_PATH=config.get('speechPath', ''),
        NOTETAKER_PROVIDER_BRIDGE_URL=config.get('bridgeURL', ''), NOTETAKER_PROVIDER_BRIDGE_TOKEN=config.get('bridgeToken', ''),
        OLLAMA_HOST='127.0.0.1:11435', OLLAMA_NO_CLOUD='1',
        OLLAMA_MODELS=str(Path.home() / '.ollama/models'))
    children, logs = [], []
    pg = root / 'postgres/bin'
    pgdata = data / 'postgres'
    def progress(message):
        print(json.dumps({'status': 'progress', 'message': message}), flush=True)
    @contextmanager
    def external_dll_path():
        # PyInstaller changes the process DLL directory; do not pass its Python
        # dependency DLLs to PostgreSQL, Seaweed or Ollama executables.
        if getattr(sys, 'frozen', False):
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            yield
        finally:
            if getattr(sys, 'frozen', False):
                ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
    def run(args, **kwargs):
        with external_dll_path(), (data / 'setup.log').open('ab') as stream:
            return subprocess.run([str(arg) for arg in args], env=env, cwd=data, check=True,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
    def launch(name, args):
        stream = (data / (name + '.log')).open('wb')
        logs.append(stream)
        with external_dll_path():
            child = subprocess.Popen([str(arg) for arg in args], env=env, cwd=data,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, creationflags=subprocess.CREATE_NO_WINDOW)
        children.append(child)
        return child
    def wait_for(check):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline and not stop.is_set():
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A bundled service stopped. Local service logs contain details.')
            try:
                if check():
                    return
            except Exception:
                pass
            stop.wait(.25)
        raise RuntimeError('Local service startup did not complete. Your library was retained.')
    try:
        progress('Opening your private PostgreSQL library…')
        if not (pgdata / 'PG_VERSION').exists():
            if pgdata.exists() and any(pgdata.iterdir()):
                raise RuntimeError('Incomplete database initialization; existing files were retained for recovery.')
            pwfile = data / 'init-password'
            try:
                pwfile.write_text(password, encoding='utf-8')
                run([pg / 'initdb.exe', '-D', pgdata, '-U', 'notetaker', '--auth=scram-sha-256',
                    '--encoding=UTF8', '--locale=C', '--pwfile', pwfile])
            finally:
                pwfile.unlink(missing_ok=True)
        if (pgdata / 'PG_VERSION').read_text().strip() != '17':
            raise RuntimeError('This database requires a supported upgrade. Existing data was retained.')
        launch('postgres', [pg / 'postgres.exe', '-D', pgdata, '-h', '127.0.0.1', '-p', '55432'])
        import psycopg
        def database_ready():
            with psycopg.connect(host='127.0.0.1', port=55432, dbname='postgres', user='notetaker', password=password, connect_timeout=2):
                return True
        wait_for(database_ready)
        progress('Opening private audio storage…')
        objects = data / 'objects'
        objects.mkdir(exist_ok=True)
        (data / 'filer.toml').write_text('[leveldb2]\nenabled = true\ndir = "' + (data / 'filer').as_posix() + '"\n')
        s3config = data / 's3.json'
        s3config.write_text(json.dumps({'identities': [{'name': 'notetaker', 'credentials': [
            {'accessKey': 'notetaker', 'secretKey': password}], 'actions': ['Admin', 'Read', 'Write', 'List', 'Tagging']}]}))
        launch('objects', [root / 'seaweed/weed.exe', 'server', '-ip=127.0.0.1', '-ip.bind=127.0.0.1',
            '-dir=' + str(objects), '-master.port=19333', '-volume.port=18080', '-filer', '-filer.port=18888',
            '-s3', '-s3.port=18333', '-s3.port.iceberg=0', '-s3.port.lance=0',
            '-s3.config=' + str(s3config), '-master.volumeSizeLimitMB=256'])
        from .config import Settings
        from .audio_store import AudioStore
        settings = Settings(_env_file=None, **{key.lower().removeprefix('notetaker_'): value for key, value in env.items() if key.startswith('NOTETAKER_')})
        store = AudioStore(settings)
        wait_for(lambda: store.ready() is None)
        executable = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).parents[1] / 'windows_service.py')]
        progress('Checking library migrations. Your existing library is retained…')
        run([*executable, 'migrate'], timeout=180)
        progress('Starting the lecture workspace API…')
        launch('api', [*executable, 'api'])
        import urllib.request
        wait_for(lambda: urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=2).status == 200)
        progress('Starting local processing workers…')
        launch('ollama', [root / 'ollama/ollama.exe', 'serve'])
        launch('notes', [*executable, 'notes'])
        if config.get('speechPath'):
            launch('speech', [*executable, 'speech'])
        print(json.dumps({'status': 'ready'}), flush=True)
        while not stop.wait(.5):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A local service stopped. Close and reopen Notetaker to recover.')
    finally:
        for child in reversed(children[1:]):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children[1:]):
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
        if children and children[0].poll() is None:
            try:
                run([pg / 'pg_ctl.exe', '-D', pgdata, 'stop', '-m', 'fast', '-w', '-t', '15'], timeout=20)
            except Exception:
                children[0].terminate()
        for stream in logs:
            stream.close()


def entry():
    try:
        main(json.loads(sys.stdin.readline()))
    except Exception as error:
        # Do not serialize subprocess arguments, provider output or credentials.
        message = str(error) if isinstance(error, RuntimeError) else 'Bundled service startup failed. Your library was retained.'
        print(json.dumps({'status': 'failed', 'message': message}), flush=True)
        return 1
    return 0
