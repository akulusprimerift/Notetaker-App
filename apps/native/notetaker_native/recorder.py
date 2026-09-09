import json
import secrets
import shutil
import threading
import time
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtMultimedia import QAudioSource, QAudioFormat, QMediaDevices, QAudio
from .client import background


class Recorder(QObject):
    status = Signal(str)

    def __init__(self, api, journal):
        super().__init__()
        self.api, self.journal = api, journal
        self.source = None
        self.run = None
        self.finishing = False
        self.buffer = bytearray()
        self.upload_stop = threading.Event()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_device)

    def start(self, lecture):
        if self.source or self.finishing:
            raise RuntimeError('A recording is already active.')
        if shutil.disk_usage(self.journal.path.parent).free < 1024**3:
            raise RuntimeError('Free at least 1 GiB before recording.')
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise RuntimeError('No recording device is available.')
        format = QAudioFormat()
        format.setSampleRate(16000)
        format.setChannelCount(1)
        format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(format):
            format.setSampleRate(device.preferredFormat().sampleRate())
        if not device.isFormatSupported(format):
            raise RuntimeError('This device does not support mono PCM recording. Select a compatible Windows input device.')
        path = '/lectures/'+lecture
        capture = self.api.get(path+'/capture')
        grant = secrets.token_urlsafe(32)
        manifest = self.api.post(path+'/capture-runs', {'sample_rate':format.sampleRate(),
                                  'expected_capture_epoch':capture['capture_epoch'], 'grant':grant})
        self.journal.start(lecture, manifest, grant)
        self.run = {**manifest, 'grant':grant, 'lecture':lecture}
        self.buffer.clear()
        self.source = QAudioSource(device, format, self)
        self.source.setBufferSize(format.sampleRate()*4)
        self.io = self.source.start()
        if self.io is None:
            self.source = None
            self.journal.stop(manifest['id'])
            raise RuntimeError('Windows could not open the input. The interrupted recording can be recovered.')
        self.io.readyRead.connect(self.read)
        self.upload_stop.clear()
        self.thread = threading.Thread(target=self.upload_loop, daemon=True)
        self.thread.start()
        self.timer.start(1000)
        self.last_tick = time.monotonic()
        self.status.emit('Recording · audio is saved locally before upload')

    def read(self):
        self.buffer.extend(bytes(self.io.readAll()))
        length = self.run['sample_rate']*4
        try:
            while len(self.buffer) >= length:
                self.journal.append(self.run['id'], bytes(self.buffer[:length]))
                del self.buffer[:length]
        except Exception as exc:
            self.source.stop()
            self.timer.stop()
            self.status.emit('Recording stopped: '+str(exc)+' Unwritten audio remains in memory; free space before closing.')

    def check_device(self):
        gap = time.monotonic()-self.last_tick
        self.last_tick = time.monotonic()
        if self.source and gap > 3:
            self.stop(gap_reason='sleep_or_suspension')
            self.status.emit('Recording stopped after a pause or suspension. Review the marked gap.')
            return
        if self.source and self.source.error() != QAudio.Error.NoError:
            self.stop(gap_reason='microphone_lost')
            self.status.emit('Recording stopped because the input was lost. Saved audio is retained; review the gap.')

    def upload(self, run):
        path = '/lectures/'+run['lecture']+'/capture-runs/'+run['id']
        for identity, raw in self.journal.pending(run['id']):
            receipt = self.api.request('PUT', path+'/chunks/'+str(identity['sequence']), content=raw,
                                      headers={'x-capture-grant':run['grant'], 'x-chunk-identity':json.dumps(identity),
                                               'content-type':'audio/wav'})
            self.journal.acknowledge(identity, receipt)

    def upload_loop(self):
        heartbeat = 0
        while not self.upload_stop.is_set():
            try:
                if time.monotonic()-heartbeat > 10:
                    self.api.post('/lectures/'+self.run['lecture']+'/capture-runs/'+self.run['id']+'/heartbeat',
                                  headers={'x-capture-grant':self.run['grant']})
                    heartbeat = time.monotonic()
                self.upload(self.run)
            except Exception as exc:
                self.status.emit('Audio retained locally. '+str(exc))
            self.upload_stop.wait(1)

    def stop(self, interrupted=False, gap_reason=None):
        if not self.source:
            return
        self.timer.stop()
        self.read()
        self.source.stop()
        if self.buffer:
            self.journal.append(self.run['id'], bytes(self.buffer))
            self.buffer.clear()
        self.source.deleteLater()
        self.source = None
        if gap_reason:
            self.journal.gap(self.run['id'],gap_reason)
        self.journal.stop(self.run['id'])
        self.upload_stop.set()
        self.finishing = True
        run = dict(self.run)
        def finish():
            self.thread.join(timeout=35)
            if self.thread.is_alive():
                raise RuntimeError('An upload is still finishing. Audio remains in the recovery journal.')
            self.recover(run, interrupted=interrupted)
        def done(_):
            self.finishing = False
            self.status.emit('Recording stopped · all captured audio verified')
        def failed(message):
            self.finishing = False
            self.status.emit('Audio retained for recovery. '+message)
        background(finish, done, failed)
        self.status.emit('Recording stopped · verifying saved audio…')

    def recover(self, run, interrupted=True):
        path = '/lectures/'+run['lecture']
        state = self.api.get(path+'/capture')
        manifest = self.api.get(path+'/capture-runs/'+run['id']+'/manifest')
        self.api.post(path+'/capture-recovery', {**self.journal.seal(run['id']), 'run_id':run['id'],
                      'grant':run['grant'], 'expected_capture_epoch':state['capture_epoch'],
                      'expected_version':manifest['manifest_version'], 'interrupted':interrupted})
        self.journal.stop(run['id'])
        self.upload(run)

    def discard_deleted(self, lecture):
        if not self.run or self.run['lecture'] != lecture:
            return
        self.timer.stop()
        if self.source:
            self.source.stop(); self.source.deleteLater(); self.source = None
        self.upload_stop.set()
        self.buffer.clear()
        self.status.emit('Recording stopped because its audio was deleted.')
