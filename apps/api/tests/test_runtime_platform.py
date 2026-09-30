import signal
import subprocess
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from notetaker import runtime_platform as platform


def test_platform_paths_and_launch_isolation(monkeypatch, tmp_path):
    assert platform.executable(tmp_path, 'postgres/bin/postgres', 'win32').name == 'postgres.exe'
    assert platform.executable(tmp_path, 'postgres/bin/postgres', 'darwin').name == 'postgres'
    with pytest.raises(RuntimeError):
        platform.executable(tmp_path, 'postgres', 'linux')
    monkeypatch.setattr(platform, 'sys', SimpleNamespace(platform='darwin'))
    monkeypatch.setattr(signal, 'SIGKILL', 9, raising=False)
    assert platform.subprocess_options() == {'start_new_session': True}


def test_mac_cleanup_signals_owned_groups_including_exited_leader(monkeypatch):
    monkeypatch.setattr(platform, 'sys', SimpleNamespace(platform='darwin'))
    monkeypatch.setattr(signal, 'SIGKILL', 9, raising=False)
    calls = []
    monkeypatch.setattr(platform.os, 'killpg', lambda *args: calls.append(args), raising=False)
    child = Mock(pid=1234)
    child.poll.return_value = 0
    platform.stop_children([child])
    assert calls == [(1234, signal.SIGTERM), (1234, signal.SIGKILL)]
    child.terminate.assert_not_called()
    child.wait.assert_called()


def test_mac_cleanup_tolerates_already_gone_group(monkeypatch):
    monkeypatch.setattr(platform, 'sys', SimpleNamespace(platform='darwin'))
    monkeypatch.setattr(signal, 'SIGKILL', 9, raising=False)
    def gone(*args):
        raise ProcessLookupError()
    monkeypatch.setattr(platform.os, 'killpg', gone, raising=False)
    platform.stop_children([Mock(pid=1234)])


def test_setup_cancellation_reaps_real_owned_process():
    stop = threading.Event()
    stop.set()
    with pytest.raises(RuntimeError, match='cancelled'):
        platform.run_command([sys.executable, '-c', 'import time; time.sleep(30)'],
            stop=stop, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_setup_command_reports_failure_without_arguments_or_secret():
    with pytest.raises(RuntimeError, match='setup command failed') as failure:
        platform.run_command([sys.executable, '-c', 'raise SystemExit(7)', 'private-secret'],
            stop=threading.Event(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert 'private-secret' not in str(failure.value)


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX real process-group check; run on Mac')
def test_posix_owned_tree_cleanup_keeps_unrelated_process(tmp_path):
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
    script = ('import subprocess,sys,time; '
              'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); '
              'print(p.pid,flush=True); time.sleep(60)')
    child = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, start_new_session=True)
    try:
        assert int(child.stdout.readline()) > 0
        platform.stop_children([child])
        assert child.poll() is not None
        assert unrelated.poll() is None
    finally:
        platform.stop_children([child, unrelated])
        child.stdout.close()
