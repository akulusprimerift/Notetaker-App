"""Operating-system boundaries for the shared standalone service supervisor."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def executable(root, relative, platform=None):
    platform = platform or sys.platform
    if platform not in ('win32', 'darwin'):
        raise RuntimeError('Standalone services support Windows and macOS only')
    return Path(root) / (relative + ('.exe' if platform == 'win32' else ''))


def subprocess_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {'start_new_session': True}


def protect_library(data):
    if sys.platform == 'win32':
        account = os.environ['USERDOMAIN'] + '\\' + os.environ['USERNAME']
        subprocess.run(['icacls', str(data), '/inheritance:r', '/grant:r', account + ':(OI)(CI)F',
            '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL, **subprocess_options())
    else:
        os.umask(0o077)
        data.chmod(0o700)


def signal_child(child, force=False):
    if sys.platform == 'win32':
        if child.poll() is None:
            child.kill() if force else child.terminate()
    else:
        # Only launch-created sessions are passed here. Never signal our own group
        # or find processes by name; a dead leader can still have owned children.
        try:
            os.killpg(child.pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:
            pass


def stop_children(children, timeout=10):
    for child in reversed(children):
        signal_child(child)
    deadline = time.monotonic() + timeout
    for child in reversed(children):
        try:
            child.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for child in reversed(children):
        signal_child(child, force=True)
        child.wait(timeout=5)


def run_command(args, *, stop, timeout=180, **kwargs):
    """Allow parent disconnect to cancel startup commands and their descendants."""
    child = subprocess.Popen(args, **kwargs, **subprocess_options())
    deadline = time.monotonic() + timeout
    try:
        while child.poll() is None:
            if stop.is_set():
                raise RuntimeError('Standalone startup was cancelled. Your library was retained.')
            if time.monotonic() >= deadline:
                raise RuntimeError('A bundled setup command timed out. Your library was retained.')
            stop.wait(.1)
        if child.returncode:
            raise RuntimeError('A bundled setup command failed. Your library was retained.')
    finally:
        stop_children([child], timeout=1)
