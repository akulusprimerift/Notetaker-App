import json
import secrets
import shutil
import threading
import time
import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtMultimedia import QAudioSource, QAudioFormat, QMediaDevices, QAudio
from .client import background


class Recorder(QObject):
    status = Signal(str)
    progress = Signal(object)

    def __init__(self, api, journal):
        super().__init__()
        self.api, self.journal = api, journal
        self.source = None
        self.run = None
        self.finishing = False
        self.starting = False
        self.captured = self.verified = 0
        self.level = 0
        self.buffer = bytearray()
        self.upload_stop = threading.Event()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_device)

    def start(self, lecture, device=None):
        if self.source or self.finishing or self.starting:
            raise RuntimeError('A recording is already active.')
        if shutil.disk_usage(self.journal.path.parent).free < 1024**3:
            raise RuntimeError('Free at least 1 GiB before recording.')
        device = device or QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise RuntimeError('No recording device is available.')
        format = QAudioFormat()
        format.setSampleRate(16000)
        format.setChannelCount(1)
        format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(format):
            format = device.preferredFormat()
        if not device.isFormatSupported(format):
            raise RuntimeError('This device has no supported audio format. Choose another input.')
        if format.sampleFormat() not in (QAudioFormat.SampleFormat.Int16, QAudioFormat.SampleFormat.Int32,
                QAudioFormat.SampleFormat.Float, QAudioFormat.SampleFormat.UInt8):
            raise RuntimeError('Unsupported input format. Choose another input.')
        self.format = format
        self.starting = True
        path = '/lectures/'+lecture
        grant = secrets.token_urlsafe(32)
        def prepare():
            capture = self.api.get(path+'/capture')
            manifest = self.api.post(path+'/capture-runs', {'sample_rate':format.sampleRate(),
                                  'expected_capture_epoch':capture['capture_epoch'], 'grant':grant})
            self.journal.start(lecture, manifest, grant)
            return manifest
        def failed(message):
            self.starting = False
            self.status.emit('Recording could not start: '+message)
        background(prepare, lambda manifest:self.open_input(device, format, lecture, manifest, grant), failed)
        self.status.emit('Opening recording · waiting for Windows audio…')

    def open_input(self, device, format, lecture, manifest, grant):
        self.starting = False
        self.run = {**manifest, 'grant':grant, 'lecture':lecture}
        self.captured = self.verified = 0
        self.buffer.clear()
        self.input_buffer = bytearray()
        self.source = QAudioSource(device, format, self)
        self.source.setBufferSize(format.bytesForDuration(200000))
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
        self.last_audio = self.last_tick
        self.last_checked_samples = 0
        self.status.emit('Input opened · waiting for audio samples…')

    @staticmethod
    def mono_pcm(raw, format):
        kind = format.sampleFormat()
        dtype, scale = {QAudioFormat.SampleFormat.Int16:('<i2', 32768),
            QAudioFormat.SampleFormat.Int32:('<i4', 2147483648),
            QAudioFormat.SampleFormat.Float:('<f4', 1),
            QAudioFormat.SampleFormat.UInt8:('u1', 128)}[kind]
        samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
        if kind == QAudioFormat.SampleFormat.UInt8: samples -= 128
        samples = np.nan_to_num(samples / scale).reshape(-1, format.channelCount()).mean(axis=1)
        level = float(np.max(np.abs(samples))) if len(samples) else 0
        return (np.clip(samples, -1, 32767/32768)*32768).astype('<i2').tobytes(), level

    def read(self):
        self.input_buffer.extend(bytes(self.io.readAll()))
        size = len(self.input_buffer)//self.format.bytesPerFrame()*self.format.bytesPerFrame()
        if size:
            pcm, self.level = self.mono_pcm(bytes(self.input_buffer[:size]), self.format)
            del self.input_buffer[:size]
            self.buffer.extend(pcm)
            self.captured += len(pcm)//2
            self.last_audio = time.monotonic()
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
        # readyRead and this timer can be delivered in either order after a busy
        # event loop. Drain queued frames before diagnosing a missing device.
        if self.source: self.read()
        captured_seconds = (self.captured-self.last_checked_samples)/self.run['sample_rate'] if self.run else 0
        self.last_checked_samples = self.captured
        if self.run:
            self.progress.emit({'seconds':self.captured/self.run['sample_rate'],
                'saved_seconds':self.verified/self.run['sample_rate'], 'level':min(100,round(self.level*100))})
        if self.source and time.monotonic()-self.last_audio > 5:
            self.stop(gap_reason='microphone_lost')
            self.status.emit('No audio samples received. Check Windows microphone permission and select another input. Saved audio is retained.')
            return
        if self.source and gap > 3 and captured_seconds < gap-2:
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
            if self.run and self.run['id'] == run['id']:
                self.verified = max(self.verified, identity['start_sample']+identity['sample_count'])

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
            self.progress.emit({'seconds':self.captured/run['sample_rate'],
                'saved_seconds':self.verified/run['sample_rate'], 'level':0})
            self.status.emit('Recording interrupted · saved audio verified. Check your input and review the marked gap.'
                if gap_reason else 'Recording stopped · all captured audio verified')
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
