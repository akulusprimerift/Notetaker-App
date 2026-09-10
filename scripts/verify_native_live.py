"""Opt-in synthetic WAV through native Recorder, real workers and live widgets."""
import argparse
import json
import time
import wave
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtMultimedia import QAudioFormat, QAudio
from PySide6.QtWidgets import QApplication
from notetaker_native import recorder as capture_module
from notetaker_native import runtime as runtime_module
from notetaker_native.client import Api, Stream, background
from notetaker_native.window import Window


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', type=Path, required=True, help='Controlled synthetic WAV only')
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--live-sections', type=int, default=0,
                        help='Require this many saved revisions before the synthetic recording stops')
    args = parser.parse_args()
    args.directory = args.directory.resolve()
    if args.directory.exists(): raise RuntimeError('Use a fresh isolated verification directory')
    with wave.open(str(args.audio), 'rb') as audio:
        assert audio.getnchannels()==1 and audio.getsampwidth()==2
        rate = audio.getframerate(); pcm = audio.readframes(audio.getnframes())
    format = QAudioFormat(); format.setSampleRate(rate); format.setChannelCount(1)
    format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    class Device:
        def isNull(self): return False
        def isFormatSupported(self, candidate): return candidate == format
        def preferredFormat(self): return format
    class Input(QObject):
        readyRead = Signal()
        def __init__(self): super().__init__(); self.at = 0; self.opened = time.monotonic()
        def readAll(self):
            end = min(len(pcm), int((time.monotonic()-self.opened)*rate)*2)
            data = pcm[self.at:end]; self.at = end; return data
    class Source(QObject):
        def __init__(self, device, requested, parent):
            super().__init__(parent); self.io = Input(); self.timer = QTimer(self)
            self.timer.timeout.connect(self.tick)
        def setBufferSize(self, size): pass
        def start(self): self.timer.start(1000); return self.io
        def tick(self):
            self.io.readyRead.emit()
            if self.io.at >= len(pcm): self.timer.stop(); window.recorder.stop()
        def stop(self): self.timer.stop()
        def error(self): return QAudio.Error.NoError
    capture_module.QAudioSource = Source
    if args.bundle:
        bundle = args.bundle.resolve()
        runtime_module.resource_root = lambda:bundle/'_internal'
        runtime_module.command = lambda mode,*rest:[str(bundle/'NotetakerService.exe'), mode, *rest]
    app = QApplication([])
    runtime = runtime_module.Runtime(args.directory)
    runtime.start()
    api = Api(runtime.url)
    window = Window(api,runtime); window.show()
    report = {'microphone_accessed':False, 'fixture':args.audio.name, 'real_models':True}
    started = time.monotonic(); previews = set(); speech_previews = set(); state = {}
    def stream_received(lecture, payload):
        if payload.get('text'): previews.add(payload['text'])
        transcript = payload.get('transcript', {})
        if transcript.get('preview'): speech_previews.add(transcript['preview'])
        if (transcript.get('snapshot') or {}).get('segments') and 'first_transcript_seconds' not in report:
            report['first_transcript_seconds'] = round(time.monotonic()-started,2)
            report['transcript_during_capture'] = bool(window.recorder.source)
        if payload.get('text') and 'first_note_preview_seconds' not in report:
            report['first_note_preview_seconds'] = round(time.monotonic()-started,2)
            window.grab().save(str(args.directory/'live.png'))
    def prepare():
        course = api.post('/courses',{'name':'Synthetic live qualification'})
        lecture = api.post('/courses/'+course['id']+'/lectures',{'title':'Binary search · synthetic speech'})
        models = api.get('/note-models')['models']
        if not models: raise RuntimeError('Select an existing local note model before this probe')
        model = next((m['name'] for m in models if m['name']=='qwen3:4b'), models[0]['name'])
        api.post('/lectures/'+lecture['id']+'/notes/model', {'model':model,'expected_version':0,'enabled':True})
        report['note_model'] = model
        return lecture
    def ready(lecture):
        nonlocal started
        window.lecture = lecture['id']; window.course = lecture['course_id']
        window.title.setText(lecture['title']); window.load_library(); window.refresh()
        stream = Stream(api,lecture['id']); stream.changed.connect(window.streaming)
        stream.changed.connect(stream_received); window.streams.append(stream); stream.thread.start()
        started = time.monotonic(); window.recorder.start(lecture['id'],Device())
    def failed(message): state['error'] = message; app.exit(1)
    background(prepare,ready,failed)
    timer = QTimer(); timer.setInterval(1000)
    def check():
        selected = window.selected()
        if selected and window.recorder.source:
            sections = report.setdefault('sections_saved_during_capture', [])
            if not sections or sections[-1]['revision'] != selected['revision']:
                sections.append({'revision':selected['revision'], 'seconds':round(time.monotonic()-started,2),
                                 'blocks':len(selected['content']['blocks'])})
        if time.monotonic()-started > max(420, len(pcm)/2/rate+180): failed('Live workflow timed out'); return
        if selected and previews and report.get('transcript_during_capture') and not window.recorder.source and not window.recorder.finishing:
            if len(report.get('sections_saved_during_capture', [])) < args.live_sections:
                failed('Too few sections were saved before recording stopped'); return
            report.update(note_preview_updates=len(previews), speech_preview_updates=len(speech_previews),
                saved_note_revision=selected['id'], captured_samples=window.recorder.captured,
                verified_samples=window.recorder.verified, duration_seconds=round(len(pcm)/2/rate,2))
            if not window.recorder.captured == window.recorder.verified == len(pcm)//2:
                failed(f'Audio counts differ: captured={window.recorder.captured}, verified={window.recorder.verified}, expected={len(pcm)//2}')
                return
            window.grab().save(str(args.directory/'complete.png'))
            app.quit()
    timer.timeout.connect(check); timer.start()
    try:
        result = app.exec()
        report.update(state)
        (args.directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
        return result
    finally:
        timer.stop()
        if window.recorder.source: window.recorder.source.stop()
        window.recorder.upload_stop.set()
        for stream in window.streams: stream.stop.set()
        runtime.close()


if __name__ == '__main__': raise SystemExit(main())
