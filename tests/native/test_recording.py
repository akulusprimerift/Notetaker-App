import time
import numpy as np
import pytest
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudio
from PySide6.QtWidgets import QApplication
from test_workspace import setup
from test_capture import capture
from notetaker_native.recorder import Recorder
from notetaker_native.journal import Journal


def wait(app, condition):
    deadline = time.monotonic()+10
    while not condition() and time.monotonic()<deadline:
        app.processEvents(); time.sleep(.01)
    assert condition()


@pytest.mark.parametrize('no_samples', [False, True])
def test_preferred_stereo_float_capture_saved_and_sealed(capture, tmp_path, monkeypatch, no_samples):
    backend, client, headers, path, prior = capture
    # Use a new lecture so no other recorder owns this synthetic run.
    course = client.get('/courses').json()[0]
    lecture = client.post('/courses/'+course['id']+'/lectures', json={'title':'PCM input'}, headers=headers).json()
    app = QApplication.instance() or QApplication([])
    format = QAudioFormat(); format.setSampleRate(48000); format.setChannelCount(2)
    format.setSampleFormat(QAudioFormat.SampleFormat.Float)
    count = 0 if no_samples else 48000*3
    frames = np.full((count,2), .25, dtype='<f4').tobytes()
    class Device:
        def isNull(self): return False
        def isFormatSupported(self, candidate): return candidate == format
        def preferredFormat(self): return format
    class Source:
        def __init__(self, *args):
            self.io = QBuffer(); self.io.setData(frames); self.io.open(QIODevice.OpenModeFlag.ReadOnly)
        def setBufferSize(self, size): pass
        def start(self): return self.io
        def stop(self): pass
        def deleteLater(self): pass
        def error(self): return QAudio.Error.NoError
    class Api:
        def request(self, method, endpoint, **kwargs):
            extra = kwargs.pop('headers', {})
            result = client.request(method, endpoint, headers={**headers, **extra}, **kwargs)
            result.raise_for_status(); return result.json()
        def get(self, endpoint): return self.request('GET',endpoint)
        def post(self, endpoint, body=None, **kwargs): return self.request('POST',endpoint,json=body or {},**kwargs)
    monkeypatch.setattr('notetaker_native.recorder.QAudioSource',Source)
    recorder = Recorder(Api(),Journal(tmp_path/'capture.db'))
    messages = []; recorder.status.connect(messages.append)
    recorder.start(lecture['id'],Device())
    wait(app,lambda:recorder.source is not None)
    if not no_samples:
        recorder.last_tick -= 4
        recorder.last_audio -= 4
        recorder.check_device()
        assert recorder.source is not None  # Buffered frames survive a late GUI timer.
    recorder.read()
    assert recorder.captured == count
    if no_samples:
        recorder.last_audio -= 6
        recorder.check_device()
        assert recorder.source is not None
        assert any('No audio samples received' in message for message in messages)
        assert not recorder.finishing
        recorder.stop()
    else:
        assert recorder.level == .25
        recorder.stop()
    wait(app,lambda:not recorder.finishing)
    assert messages[-1] == 'Recording stopped · all captured audio verified'
    manifest = client.get('/lectures/'+lecture['id']+'/capture-runs/'+recorder.run['id']+'/manifest').json()
    assert manifest['complete'] and manifest['final_sample_count'] == count
    if no_samples: assert manifest['gaps'] == []
    assert recorder.verified == recorder.captured
    assert not recorder.journal.pending(recorder.run['id'])
