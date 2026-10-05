"""Shared standalone SQLite library and local inference service tree."""
import ctypes
from contextlib import contextmanager, closing
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import threading
import time

from .runtime_platform import executable, protect_library, run_command, stop_children, subprocess_options


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
            if sys.platform == 'win32':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                raise RuntimeError(f'Port {port} is in use. Close the other workspace before starting this library.') from None


def require_sqlite_library(data):
    # Conversion is explicit and side by side; never open a legacy directory as empty.
    if (data / 'postgres').exists() or (data / 'PG_VERSION').exists():
        raise RuntimeError('This library uses PostgreSQL. Convert it to a separate SQLite library before opening it. Existing files were retained.')
    filename = data / 'workspace.sqlite3'
    if not filename.resolve().is_relative_to(data.resolve()):
        raise RuntimeError('The library database must stay inside its library folder.')
    if filename.exists():
        import sqlite3
        with closing(sqlite3.connect(filename.as_uri() + '?mode=ro', uri=True)) as connection:
            if connection.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise RuntimeError('The SQLite library needs recovery. Existing files were retained.')


def main(config):
    if sys.platform not in ('win32', 'darwin'):
        raise RuntimeError('Standalone services support Windows and macOS only')
    if sys.platform == 'win32':
        owned_job = own_process_tree()
        assert owned_job
    root = Path(config['resources']).resolve()
    data = Path(config['data']).resolve()
    data.mkdir(parents=True, exist_ok=True)
    protect_library(data)
    require_sqlite_library(data)
    require_free_ports([3000, 8010, 11435])
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    def watch_parent():
        for _ in sys.stdin:
            stop.set()
            return
        stop.set()
    threading.Thread(target=watch_parent, daemon=True).start()
    env = {key: value for key, value in os.environ.items() if not key.startswith(('NOTETAKER_', 'PG', 'OLLAMA_', 'PYTHON'))}
    env.update(NOTETAKER_DATABASE_URL='sqlite:///' + (data / 'workspace.sqlite3').as_posix(),
        PYINSTALLER_RESET_ENVIRONMENT='1',
        NOTETAKER_PREVIEW='false', NOTETAKER_STANDALONE='true', NOTETAKER_AUDIO_DIRECTORY=str(data / 'audio'),
        NOTETAKER_OLLAMA_URL='http://127.0.0.1:11435',
        NOTETAKER_WEB_ORIGIN='http://127.0.0.1:3000', NOTETAKER_SPEECH_MODEL_PATH=config.get('speechPath', ''),
        NOTETAKER_SPEECH_STATUS_PATH=str(data / 'speech-status.json'), NOTETAKER_SPEECH_STATUS_SESSION=os.urandom(16).hex(),
        NOTETAKER_PROVIDER_BRIDGE_URL=config.get('bridgeURL', ''), NOTETAKER_PROVIDER_BRIDGE_TOKEN=config.get('bridgeToken', ''),
        OLLAMA_HOST='127.0.0.1:11435', OLLAMA_NO_CLOUD='1',
        OLLAMA_MODELS=str(Path.home() / '.ollama/models'))
    children, logs = [], []
    def progress(message):
        print(json.dumps({'status': 'progress', 'message': message}), flush=True)
    @contextmanager
    def external_dll_path():
        # PyInstaller changes the process DLL directory; do not pass its Python
        # dependency DLLs to Ollama executables.
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            yield
        finally:
            if sys.platform == 'win32' and getattr(sys, 'frozen', False):
                ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
    def run(args, *, shutting_down=False, **kwargs):
        with external_dll_path(), (data / 'setup.log').open('ab') as stream:
            return run_command([str(arg) for arg in args], stop=threading.Event() if shutting_down else stop, env=env, cwd=data,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                **kwargs)
    def launch(name, args):
        stream = (data / (name + '.log')).open('wb')
        logs.append(stream)
        with external_dll_path():
            child = subprocess.Popen([str(arg) for arg in args], env=env, cwd=data,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, **subprocess_options())
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
        progress('Opening your private SQLite library…')
        from .config import Settings
        from .audio_store import AudioStore
        settings = Settings(_env_file=None, **{key.lower().removeprefix('notetaker_'): value for key, value in env.items() if key.startswith('NOTETAKER_')})
        AudioStore(settings).ready()
        service_command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).parents[1] / 'windows_service.py')]
        progress('Checking library migrations. Your existing library is retained…')
        run([*service_command, 'migrate'], timeout=180)
        progress('Starting the lecture workspace API…')
        launch('api', [*service_command, 'api'])
        import urllib.request
        wait_for(lambda: urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=2).status == 200)
        progress('Starting local processing workers…')
        launch('ollama', [executable(root, 'ollama/ollama'), 'serve'])
        launch('notes', [*service_command, 'notes'])
        # Keep reconciliation alive even without a model: saved audio must acquire
        # visible retryable model_unavailable jobs rather than wait silently.
        launch('speech', [*service_command, 'speech'])
        print(json.dumps({'status': 'ready'}), flush=True)
        while not stop.wait(.5):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A local service stopped. Close and reopen Notetaker to recover.')
    finally:
        stop_children(children)
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
