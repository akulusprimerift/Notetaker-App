import socket
import sys
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from notetaker.config import Settings
from notetaker.windows_host import require_free_ports
from notetaker import windows_host as host, runtime_platform


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows exclusive socket semantics')
def test_native_host_refuses_an_occupied_port_without_touching_listener():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(RuntimeError, match='in use'):
            require_free_ports([port])
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            assert listener.fileno() != -1


def test_native_brokerless_profile_retains_postgres_and_private_object_store():
    settings = Settings(_env_file=None, broker_enabled=False, database_url='postgresql+psycopg://test:test@127.0.0.1:55432/postgres')
    assert not settings.broker_enabled
    assert not settings.preview and not settings.standalone
    assert Settings(_env_file=None).broker_enabled


@pytest.mark.parametrize('target', ['win32', 'darwin'])
@pytest.mark.parametrize('failure', [False, True])
def test_shared_host_startup_and_partial_failure_cleanup(monkeypatch, tmp_path, target, failure):
    import psycopg
    import urllib.request
    from notetaker.audio_store import AudioStore

    data = tmp_path / 'library'
    (data / 'postgres').mkdir(parents=True)
    (data / 'postgres/PG_VERSION').write_text('17')
    (data / 'student-sentinel').write_bytes(b'preserve student data')
    fake_sys = SimpleNamespace(platform=target, executable=sys.executable)
    monkeypatch.setattr(host, 'sys', fake_sys)
    monkeypatch.setattr(runtime_platform, 'sys', fake_sys)
    monkeypatch.setattr(host, 'own_process_tree', lambda: 1)
    monkeypatch.setattr(host, 'protect_library', lambda _: None)
    monkeypatch.setattr(host, 'require_free_ports', lambda _: None)
    monkeypatch.setattr(host.signal, 'signal', lambda *_: None)
    monkeypatch.setattr(host.threading, 'Thread', lambda **_: SimpleNamespace(start=lambda: None))
    stop = threading.Event()
    monkeypatch.setattr(host.threading, 'Event', lambda: stop)
    statuses, launched, stopped, commands = [], [], [], []
    def output(value, **_):
        statuses.append(json.loads(value))
        if statuses[-1]['status'] == 'ready':
            stop.set()
    monkeypatch.setattr(host, 'print', output, raising=False)
    def launch(args, **options):
        if failure and len(launched) == 1:
            raise OSError('synthetic object startup failure')
        child = MagicMock()
        child.poll.return_value = None
        launched.append((args, options, child))
        return child
    monkeypatch.setattr(host.subprocess, 'Popen', launch)
    monkeypatch.setattr(host, 'run_command', lambda args, **kwargs: commands.append(args))
    monkeypatch.setattr(host, 'stop_children', lambda children: stopped.extend(children))
    monkeypatch.setattr(psycopg, 'connect', lambda **_: MagicMock())
    monkeypatch.setattr(AudioStore, 'ready', lambda _: None)
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *_, **__: SimpleNamespace(status=200))
    config = {'resources': str(tmp_path / 'runtime'), 'data': str(data), 'secret': 'synthetic-secret'}
    if failure:
        with pytest.raises(OSError, match='synthetic'):
            host.main(config)
    else:
        host.main(config)
        assert statuses[-1]['status'] == 'ready'
        assert len(launched) == 6  # Includes speech reconciliation without a selected model.
        assert launched[1][0][0].endswith('weed.exe' if target == 'win32' else 'weed')
        assert '-volume.max=0' in launched[1][0]  # The default 8-volume cap refused uploads once full.
        assert launched[3][0][0].endswith('ollama.exe' if target == 'win32' else 'ollama')
    assert launched[0][0][0].endswith('postgres.exe' if target == 'win32' else 'postgres')
    assert stopped[-1] is launched[0][2]  # Database stops after the workers.
    assert set(stopped) == {row[2] for row in launched}
    assert any('pg_ctl' in command[0] for command in commands)
    assert ('start_new_session' in launched[0][1]) == (target == 'darwin')
    assert 'synthetic-secret' not in json.dumps(statuses)
    assert (data / 'student-sentinel').read_bytes() == b'preserve student data'
