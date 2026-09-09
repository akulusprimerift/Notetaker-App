import os
import subprocess
import sys
import pytest
from notetaker_native.process_job import ProcessJob


@pytest.mark.skipif(os.name!='nt',reason='Windows process ownership')
def test_closing_native_job_terminates_its_owned_child():
    job = ProcessJob()
    child = subprocess.Popen([sys.executable,'-c','import time; print("ready",flush=True); time.sleep(30)'],
                             stdout=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        job.assign(child)
        assert child.stdout.readline().strip() == b'ready'
        assert child.poll() is None
        job.close()
        child.wait(timeout=5)
    finally:
        job.close()
        if child.poll() is None:
            child.kill(); child.wait(timeout=5)
