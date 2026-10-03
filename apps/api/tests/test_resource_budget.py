import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy.engine import URL
from notetaker.db import database
from notetaker.resource_budget import inference_slot


_LOCK_PROBE = r"""
import sys
from notetaker.db import database
from notetaker.resource_budget import inference_slot

engine, sessions = database(sys.argv[1])
with inference_slot(sessions) as acquired:
    print(str(acquired).lower(), flush=True)
engine.dispose()
"""


def test_inference_slot_excludes_another_process_for_same_sqlite_library(tmp_path):
    root = Path(__file__).resolve().parents[3]
    database_path = tmp_path / 'workspace.sqlite3'
    database_url = URL.create('sqlite', database=str(database_path)).render_as_string(hide_password=False)
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join((str(root / 'apps/api'), env.get('PYTHONPATH', '')))

    engine, sessions = database(database_url)
    try:
        with inference_slot(sessions) as acquired:
            assert acquired
            contender = subprocess.run(
                [sys.executable, '-c', _LOCK_PROBE, database_url],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            assert contender.stdout.strip() == 'false'
    finally:
        engine.dispose()
    released = subprocess.run(
        [sys.executable, '-c', _LOCK_PROBE, database_url],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert released.stdout.strip() == 'true'
