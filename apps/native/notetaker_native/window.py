"""Qt Widgets library and study workspace. No HTML, WebView or browser engine."""
import base64
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer, QBuffer, QIODevice, QUrl
from PySide6.QtGui import QTextCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem, QSplitter, QTabWidget,
    QPlainTextEdit, QListWidget, QListWidgetItem, QInputDialog, QMessageBox, QFileDialog,
    QDialog, QDialogButtonBox, QFormLayout, QProgressBar)
from .client import background, Stream
from .theme import stylesheet
from .journal import Journal
from .recorder import Recorder


def button(label, callback, layout):
    item = QPushButton(label)
    item.clicked.connect(callback)
    layout.addWidget(item)
    return item


def prose(revision):
    if not revision:
        return 'Your detailed notes will appear here as your lecture is processed.'
    return '\n\n'.join(block['topic']+'\n'+ '\n\n'.join(p['text'] for p in block['passages'])
                       for block in revision['content']['blocks'])


def update_text(field, text):
    """Append streamed suffixes without resetting the reader's selection or scroll."""
    previous = field.toPlainText()
    if previous == text: return
    scroll = field.verticalScrollBar(); position = scroll.value()
    follow = position >= scroll.maximum()-10
    if text.startswith(previous):
        cursor = QTextCursor(field.document()); cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text[len(previous):])
    else:
        selection = field.textCursor()
        anchor, at = selection.anchor(), selection.position()
        field.setPlainText(text)
        selection = field.textCursor(); selection.setPosition(min(anchor,len(text)))
        selection.setPosition(min(at,len(text)), QTextCursor.MoveMode.KeepAnchor); field.setTextCursor(selection)
    scroll.setValue(scroll.maximum() if follow else position)


class Window(QMainWindow):
    def __init__(self, api, runtime):
        super().__init__()
        self.api, self.runtime = api, runtime
        self.course = self.lecture = None
        self.state = None
        self.streams = []
        self.polling = False
        self.cleaning = False
        self.models_polling = False
        self.rendered = None
        self.transcript_rows = []
        self.material_rows = None
        self.setWindowTitle('Notetaker')
        self.resize(1260, 850)
        self.setMinimumSize(850, 600)
        self.journal = Journal(runtime.directory/'recordings.db')
        self.recorder = Recorder(api, self.journal)
        self.recorder.status.connect(self.recording_message)
        self.recorder.progress.connect(self.recording_progress)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 12, 24, 16); layout.setSpacing(18)
        top = QHBoxLayout()
        heading = QLabel('Notetaker'); heading.setObjectName('heading')
        top.addWidget(heading); top.addStretch()
        top.addWidget(QLabel('Theme'))
        self.theme = QComboBox(); self.theme.addItems(['Slate', 'Midnight'])
        self.theme.setAccessibleName('App theme')
        self.theme.setCurrentText(runtime.config.get('theme', 'Slate'))
        self.theme.currentTextChanged.connect(self.change_theme)
        top.addWidget(self.theme)
        button('Local models', self.models, top)
        layout.addLayout(top)
        splitter = QSplitter(); layout.addWidget(splitter)
        library = QWidget(); library.setObjectName('library'); left = QVBoxLayout(library)
        left.setSpacing(10)
        label = QLabel('Your library'); label.setObjectName('subheading'); left.addWidget(label)
        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName('Courses and lectures')
        self.tree.itemSelectionChanged.connect(self.select)
        left.addWidget(self.tree)
        button('New course', self.new_course, left)
        button('New lecture', self.new_lecture, left)
        button('Delete course', self.delete_course, left)
        button('Delete lecture', self.delete_lecture, left)
        button('Course materials', lambda:self.upload_material(True), left)
        button('Recover saved audio', self.recover, left)
        splitter.addWidget(library)
        workspace = QWidget(); main = QVBoxLayout(workspace)
        self.title = QLabel('Choose a lecture'); self.title.setObjectName('subheading'); main.addWidget(self.title)
        self.title.setWordWrap(True)
        self.capture_status = QLabel('Ready to record · choose a lecture and input'); self.capture_status.setWordWrap(True)
        self.capture_status.setTextFormat(Qt.TextFormat.PlainText); main.addWidget(self.capture_status)
        recording = QHBoxLayout(); main.addLayout(recording)
        self.input = QComboBox(); self.input.setAccessibleName('Recording input')
        recording.addWidget(self.input, 1)
        self.devices = QMediaDevices(self); self.devices.audioInputsChanged.connect(self.refresh_inputs)
        self.refresh_inputs()
        self.clock = QLabel('00:00 captured · 00:00 saved'); recording.addWidget(self.clock)
        self.meter = QProgressBar(); self.meter.setRange(0,100); self.meter.setValue(0)
        self.meter.setAccessibleName('Input audio level'); self.meter.setTextVisible(False); self.meter.setMaximumWidth(100)
        recording.addWidget(self.meter)
        actions = QHBoxLayout(); main.addLayout(actions)
        self.record_button = button('Record', self.record, actions); self.record_button.setObjectName('primary')
        self.stop_button = button('Stop and save', self.stop_recording, actions); self.stop_button.setEnabled(False)
        button('Add slides / materials', lambda:self.upload_material(False), actions)
        button('Finalize', self.finalize, actions)
        button('Export', self.export, actions)
        self.pipeline_status = QLabel('Transcription ready · select a local note model in Note preferences')
        self.pipeline_status.setWordWrap(True); self.pipeline_status.setTextFormat(Qt.TextFormat.PlainText)
        main.addWidget(self.pipeline_status)
        self.tabs = QTabWidget(); main.addWidget(self.tabs)
        notes_page = QWidget(); notes_layout = QVBoxLayout(notes_page)
        self.notes = QPlainTextEdit(); self.notes.setReadOnly(True); self.notes.setAccessibleName('Saved study notes')
        self.notes.setPlaceholderText('Your saved study notes will appear here. Follow live transcription and writing below.')
        self.notes.setMaximumHeight(100)
        notes_layout.addWidget(self.notes, 3)
        edit_actions = QHBoxLayout(); notes_layout.addLayout(edit_actions)
        button('Edit a passage', self.edit_passage, edit_actions)
        button('Add my notes', self.add_notes, edit_actions)
        button('Compare suggestion', self.compare, edit_actions)
        button('History / undo', self.history, edit_actions)
        button('Inspect source', self.source, edit_actions)
        self.review = QWidget(); review_layout = QHBoxLayout(self.review)
        self.review_text = QLabel(); self.review_text.setWordWrap(True); self.review_text.setTextFormat(Qt.TextFormat.PlainText)
        review_layout.addWidget(self.review_text, 1)
        dismiss = button('×', self.dismiss_review, review_layout)
        dismiss.setAccessibleName('Dismiss Worth reviewing'); dismiss.setMaximumWidth(44)
        notes_layout.addWidget(self.review)
        self.show_review = button('Show review notices', self.restore_review, notes_layout)
        self.preview = QPlainTextEdit(); self.preview.setReadOnly(True)
        self.preview.setPlaceholderText('Live writing preview · source checks run before notes are saved')
        self.preview.setAccessibleName('Streaming note preview'); notes_layout.addWidget(self.preview, 1)
        live = QSplitter(Qt.Orientation.Horizontal)
        live_notes = QWidget(); live_notes_layout = QVBoxLayout(live_notes)
        live_notes_layout.setContentsMargins(0,0,0,0)
        live_notes_layout.addWidget(QLabel('Live notes · preview before source checks'))
        live_notes_layout.addWidget(self.preview)
        live.addWidget(live_notes)
        live_speech = QWidget(); live_speech_layout = QVBoxLayout(live_speech)
        live_speech_layout.setContentsMargins(0,0,0,0)
        live_speech_layout.addWidget(QLabel('Live transcript · recognized speech'))
        self.live_transcript = QPlainTextEdit(); self.live_transcript.setReadOnly(True)
        self.live_transcript.setAccessibleName('Live transcript')
        self.live_transcript.setPlaceholderText('Speech appears during recording after the first audio window is saved.')
        live_speech_layout.addWidget(self.live_transcript); live.addWidget(live_speech)
        notes_layout.addWidget(live, 2)
        self.tabs.addTab(notes_page, 'Study notes')
        self.transcript = QListWidget(); self.transcript.setWordWrap(True)
        self.transcript.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.transcript.itemDoubleClicked.connect(self.correct_transcript)
        self.tabs.addTab(self.transcript, 'Transcript')
        self.materials = QListWidget(); self.tabs.addTab(self.materials, 'Materials')
        prompts = QWidget(); form = QFormLayout(prompts)
        self.model = QComboBox(); self.model.setAccessibleName('Note model'); form.addRow('Note model', self.model)
        model_help = QLabel('Choose a lecture in the library, then select a local model here. If this list is empty, open Local models first.')
        model_help.setWordWrap(True); form.addRow(model_help)
        self.prompts = {}
        for key, label in [('detail_prompt','Detail instructions'), ('layout_prompt','Layout instructions'), ('instructions','Writing instructions')]:
            field = QPlainTextEdit(); field.setMaximumHeight(105); field.setAccessibleName(label)
            self.prompts[key] = field; form.addRow(label, field)
        prompt_actions = QHBoxLayout(); form.addRow(prompt_actions)
        button('Apply and write notes', self.generate, prompt_actions)
        button('Load profile', self.load_profile, prompt_actions)
        button('Save profile', self.save_profile, prompt_actions)
        self.tabs.addTab(prompts, 'Note preferences')
        splitter.addWidget(workspace); splitter.setSizes([250, 1000])
        self.change_theme(self.theme.currentText())
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(2000)
        self.cleanup_timer = QTimer(self); self.cleanup_timer.timeout.connect(self.cleanup); self.cleanup_timer.start(4000)
        self.load_library()
        self.model_timer = QTimer(self); self.model_timer.timeout.connect(self.refresh_models)
        self.model_timer.start(3000)
        self.refresh_models()
        self.message('Private local library · no browser engine · models stay on this computer')

    def message(self, text):
        self.statusBar().showMessage(text)

    def refresh_inputs(self):
        selected = self.input.currentData()
        self.input.clear()
        default = QMediaDevices.defaultAudioInput()
        for device in QMediaDevices.audioInputs():
            self.input.addItem(device.description(), device)
            if (selected and device.id() == selected.id()) or (not selected and device.id() == default.id()):
                self.input.setCurrentIndex(self.input.count()-1)

    def recording_message(self, text):
        self.capture_status.setText(text)
        busy = bool(self.recorder.source or self.recorder.starting or self.recorder.finishing)
        recording = bool(self.recorder.source)
        self.record_button.setEnabled(not busy); self.input.setEnabled(not busy)
        self.record_button.setText('● Recording…' if recording else 'Record')
        self.record_button.setProperty('recording', recording)
        self.record_button.style().unpolish(self.record_button); self.record_button.style().polish(self.record_button)
        self.stop_button.setEnabled(bool(self.recorder.source))

    def recording_progress(self, progress):
        def stamp(seconds): return f'{int(seconds)//60:02d}:{int(seconds)%60:02d}'
        self.clock.setText(stamp(progress['seconds'])+' captured · '+stamp(progress['saved_seconds'])+' saved')
        self.meter.setValue(progress['level'])
        if self.recorder.source:
            self.record_button.setText('● Recording…')
            self.capture_status.setText('Recording · '+('audio detected' if progress['level'] else 'input is silent; check your microphone'))

    def error(self, text):
        self.message(text)
        QMessageBox.warning(self, 'Could not complete the action', text)

    def work(self, function, done=None):
        background(function, done or (lambda _:self.refresh()), self.error)

    def change_theme(self, theme):
        if self.theme.currentText() != theme:
            self.theme.blockSignals(True); self.theme.setCurrentText(theme); self.theme.blockSignals(False)
        self.setStyleSheet(stylesheet(theme))
        self.runtime.config['theme'] = theme
        self.runtime.save_config()

    def load_library(self):
        def fetch():
            return [(course, self.api.get('/courses/'+course['id']+'/lectures')) for course in self.api.get('/courses')]
        def display(rows):
            self.tree.blockSignals(True); self.tree.clear()
            for course, lectures in rows:
                parent = QTreeWidgetItem([course['name']]); parent.setData(0, Qt.ItemDataRole.UserRole, ('course',course))
                self.tree.addTopLevelItem(parent)
                for lecture in lectures:
                    child = QTreeWidgetItem([lecture['title']]); child.setData(0, Qt.ItemDataRole.UserRole, ('lecture',lecture))
                    parent.addChild(child)
                    if lecture['id'] == self.lecture: self.tree.setCurrentItem(child)
                parent.setExpanded(True)
            self.tree.blockSignals(False)
        self.work(fetch, display)

    def select(self):
        item = self.tree.currentItem()
        if not item: return
        kind, data = item.data(0, Qt.ItemDataRole.UserRole)
        self.course = data['id'] if kind == 'course' else data['course_id']
        self.lecture = data['id'] if kind == 'lecture' else None
        self.title.setText(data['name'] if kind == 'course' else data['title'])
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.state = None; self.rendered = None; self.notes.clear(); self.preview.clear(); self.transcript.clear(); self.materials.clear()
        self.notes.setMaximumHeight(100)
        self.transcript_rows = []; self.material_rows = None; self.live_transcript.clear()
        for stream in self.streams: stream.stop.set()
        if self.lecture:
            stream = Stream(self.api, self.lecture); stream.changed.connect(self.streaming)
            self.streams.append(stream); stream.thread.start()
            self.refresh()

    def require_lecture(self):
        if not self.lecture:
            self.message('Choose a lecture first.'); return False
        return True

    def new_course(self):
        name, ok = QInputDialog.getText(self, 'New course', 'Course name')
        if ok and name.strip(): self.work(lambda:self.api.post('/courses', {'name':name.strip()}), lambda _:self.load_library())

    def new_lecture(self):
        if not self.course: self.message('Choose a course first.'); return
        course = self.course
        title, ok = QInputDialog.getText(self, 'New lecture', 'Lecture title')
        def created(row):
            self.lecture = row['id']; self.title.setText(row['title']); self.load_library()
            self.state = None; self.rendered = None; self.transcript_rows = []; self.material_rows = None
            self.notes.clear(); self.preview.clear(); self.transcript.clear(); self.live_transcript.clear()
            for stream in self.streams: stream.stop.set()
            stream = Stream(self.api, self.lecture); stream.changed.connect(self.streaming)
            self.streams.append(stream); stream.thread.start(); self.refresh()
        if ok and title.strip(): self.work(lambda:self.api.post('/courses/'+course+'/lectures', {'title':title.strip()}), created)

    def delete_lecture(self):
        if not self.require_lecture(): return
        if self.recorder.source or self.recorder.starting or self.recorder.finishing:
            self.message('Stop and save recording before deleting a lecture.'); return
        lecture = self.lecture
        def confirm(state):
            if lecture != self.lecture: return
            if QMessageBox.question(self, 'Delete lecture',
                    'Delete this lecture, its recording, transcript, materials and notes? This cannot be undone. Other lectures are kept.') != QMessageBox.StandardButton.Yes: return
            def erase():
                result = self.api.post('/lectures/'+lecture+'/deletion',
                    {'kind':'lecture', 'expected_cursor':state['cursor']})
                self.journal.purge(lecture)
                for path in self.runtime.directory.glob('draft-'+lecture+'-*'): path.unlink(missing_ok=True)
                return result
            def done(_):
                if self.lecture == lecture:
                    self.lecture = None; self.state = None; self.title.setText('Choose a lecture')
                    self.notes.clear(); self.preview.clear(); self.transcript.clear(); self.live_transcript.clear(); self.materials.clear()
                    for stream in self.streams: stream.stop.set()
                self.load_library(); self.message('Lecture deleted. Recording cleanup continues in the background.')
            self.work(erase, done)
        self.work(lambda:self.api.get('/lectures/'+lecture+'/finalization'), confirm)

    def delete_course(self):
        if not self.course: return
        course = self.course
        def confirm(rows):
            if QMessageBox.question(self, 'Delete course', f'Delete this course and all {len(rows)} lectures, recordings, materials and notes? This cannot be undone.') != QMessageBox.StandardButton.Yes: return
            def erase():
                result = self.api.post('/courses/'+course+'/deletion', {'expected_lecture_ids':[r['id'] for r in rows]})
                for row in rows:
                    self.journal.purge(row['id'])
                    for path in self.runtime.directory.glob('draft-'+row['id']+'-*'): path.unlink()
                return result
            def done(_):
                self.lecture = None; self.course = None; self.state = None
                self.notes.clear(); self.preview.clear(); self.transcript.clear(); self.materials.clear()
                self.load_library(); self.message('Course removed. Recording cleanup continues in the background.')
            if self.recorder.source or self.recorder.starting or self.recorder.finishing:
                self.error('Stop the recording before deleting a course.'); return
            self.work(erase, done)
        self.work(lambda:self.api.get('/courses/'+course+'/lectures'), confirm)

    def refresh(self):
        if not self.lecture or self.polling: return
        lecture = self.lecture; self.polling = True
        def fetch():
            return (self.api.get('/lectures/'+lecture+'/notes'), self.api.get('/lectures/'+lecture+'/transcript'),
                    self.api.get('/lectures/'+lecture+'/materials'))
        def done(result):
            self.polling = False
            if lecture != self.lecture: return
            state, transcript, materials = result
            first = self.state is None; self.state = state
            selected = state['editing']['selected'] or state['revision']
            if selected and selected['id'] != self.rendered:
                self.notes.setMaximumHeight(16777215)
                self.rendered = selected['id']; update_text(self.notes, prose(selected))
                if state['status'] not in ('generating', 'running'): self.preview.clear()
            if first:
                for key, field in self.prompts.items(): field.setPlainText(state['profile'][key])
                if state['preference']: self.model.setCurrentText(state['preference']['model'])
            self.update_review(selected)
            self.render_transcript(transcript)
            if materials != self.material_rows:
                self.material_rows = materials; self.materials.clear()
                for material in materials: self.materials.addItem(material['name']+' · '+material['kind'])
        def failed(text):
            self.polling = False; self.message(text)
        background(fetch, done, failed)

    def cleanup(self):
        if self.cleaning: return
        self.cleaning = True
        def run():
            rows = self.api.get('/deletions')
            for row in rows:
                lecture = row['lecture_id']
                self.journal.purge(lecture)
                if row['kind'] == 'lecture':
                    for path in self.runtime.directory.glob('draft-'+lecture+'-*'): path.unlink(missing_ok=True)
                if not row['browser_ack']: self.api.post('/deletions/'+row['id']+'/browser-purged')
            return rows
        def done(rows):
            self.cleaning = False
            for row in rows: self.recorder.discard_deleted(row['lecture_id'])
            if any(row['lecture_id'] == self.lecture and row['kind'] == 'lecture' for row in rows):
                self.lecture = None; self.state = None
                for stream in self.streams: stream.stop.set()
                self.notes.clear(); self.preview.clear(); self.transcript.clear(); self.materials.clear(); self.load_library()
        def failed(text):
            self.cleaning = False; self.message(text)
        background(run, done, failed)

    def streaming(self, lecture, payload):
        if lecture != self.lecture: return
        if 'transcript' in payload: self.render_transcript(payload['transcript'])
        # Retain the last preview until the validated saved revision arrives.
        if payload.get('text'): update_text(self.preview, payload['text'])

    def render_transcript(self, transcript):
        segments = (transcript.get('snapshot') or {}).get('segments', [])
        lines = []
        scroll = self.transcript.verticalScrollBar(); position = scroll.value()
        follow = position >= scroll.maximum()-10
        for index, segment in enumerate(segments):
            seconds = segment['start_sample']/segment['sample_rate']
            line = f'{int(seconds//60):02d}:{int(seconds%60):02d}  '+segment['text']; lines.append(line)
            if index < len(self.transcript_rows) and self.transcript_rows[index] == segment: continue
            if index >= self.transcript.count(): self.transcript.addItem(QListWidgetItem())
            item = self.transcript.item(index); item.setText(line); item.setData(Qt.ItemDataRole.UserRole, segment)
        while self.transcript.count() > len(segments): self.transcript.takeItem(self.transcript.count()-1)
        self.transcript_rows = segments
        scroll.setValue(scroll.maximum() if follow else position)
        preview = transcript.get('preview', '')
        update_text(self.live_transcript, '\n\n'.join(lines)+ ('\n\nRecognizing · preview\n'+preview if preview else ''))
        errors = transcript.get('errors', [])
        speech = 'Speech model unavailable; open Local models' if 'model_unavailable' in errors else transcript['status'].replace('_',' ')
        note_state = self.state or {}
        note_status = note_state.get('status','waiting for transcript').replace('_',' ')
        if not note_state.get('preference'): note_status = 'choose a model in Note preferences'
        self.pipeline_status.setText('Transcription: '+speech+' · '+str(transcript.get('processing_delay_seconds',0))+
            's pending    |    Notes: '+note_status+((' · '+note_state['error_code']) if note_state.get('error_code') else ''))

    def update_review(self, revision):
        issues = revision['content']['issues'] if revision else []
        self.review_text.setText('Worth reviewing\n'+'\n'.join(i['detail'] for i in issues))
        hidden = self.runtime.config.get('review_hidden', {}).get(self.lecture) == (revision or {}).get('id')
        self.review.setVisible(bool(issues) and not hidden); self.show_review.setVisible(bool(issues) and hidden)

    def dismiss_review(self):
        self.runtime.config.setdefault('review_hidden', {})[self.lecture] = self.rendered
        self.runtime.save_config(); self.review.hide(); self.show_review.show()

    def restore_review(self):
        self.runtime.config.setdefault('review_hidden', {}).pop(self.lecture, None)
        self.runtime.save_config(); self.review.show(); self.show_review.hide()

    def upload_material(self, course_scope):
        if not self.course or (not course_scope and not self.require_lecture()): return
        path = '/courses/'+self.course if course_scope else '/lectures/'+self.lecture
        filename, _ = QFileDialog.getOpenFileName(self, 'Add course evidence', '', 'Course materials (*.pptx *.docx *.pdf *.txt *.md)')
        if not filename: return
        kind, ok = QInputDialog.getItem(self, 'Material type', 'Use this as', ['slides','syllabus','curriculum'], editable=False)
        if not ok: return
        def upload():
            source = Path(filename)
            if source.stat().st_size > 8*1024*1024: raise ValueError('Choose a file smaller than 8 MiB.')
            rows = self.api.get(path+'/materials')
            return self.api.post(path+'/materials', {'name':source.name, 'kind':kind, 'expected_count':len(rows),
                                 'data':base64.b64encode(source.read_bytes()).decode('ascii')})
        self.work(upload, lambda _:(self.message('Material saved. Notes will use this evidence; your edits stay protected.'), self.refresh()))

    def refresh_models(self):
        if self.models_polling: return
        self.models_polling = True
        def done(data):
            self.models_polling = False
            current = self.model.currentText(); self.model.clear()
            self.model.addItems([m['name'] for m in data['models']])
            if current: self.model.setCurrentText(current)
            if data['models']: self.model_timer.stop()
        def failed(text):
            self.models_polling = False; self.message(text)
        background(lambda:self.api.get('/note-models'), done, failed)

    def models(self):
        dialog = QDialog(self); dialog.setWindowTitle('Local models'); form = QVBoxLayout(dialog)
        label = QLabel('Speech recognition includes a local faster-whisper model. You can select a different speech model.\nFor study notes, select your local Ollama or GGUF model files.'); label.setWordWrap(True); form.addWidget(label)
        found = self.runtime.detected
        display = QPlainTextEdit(); display.setReadOnly(True)
        display.setPlainText('\n'.join(['Detected model locations:', *found['ollama'], *found['gguf'], *found['speech']]) or 'No models detected')
        form.addWidget(display)
        def speech():
            folder = QFileDialog.getExistingDirectory(dialog, 'Select a faster-whisper model folder')
            if folder:
                if not (Path(folder)/'model.bin').is_file() or not (Path(folder)/'config.json').is_file():
                    self.error('Select a faster-whisper folder containing model.bin and config.json.'); return
                self.runtime.config['speech_model'] = folder; self.runtime.save_config()
                self.message('Speech model selected. Restart Notetaker to apply.'); dialog.accept()
        def existing():
            folder = QFileDialog.getExistingDirectory(dialog, 'Select an existing Ollama models folder')
            if folder:
                if not (Path(folder)/'manifests').is_dir(): self.error('Choose the folder containing manifests and blobs.'); return
                self.runtime.config['ollama_models'] = folder; self.runtime.save_config()
                self.message('Existing models selected. Restart Notetaker to apply.'); dialog.accept()
        def gguf():
            filename, _ = QFileDialog.getOpenFileName(dialog, 'Import a local Qwen GGUF', '', 'Model weights (*.gguf)')
            if not filename: return
            def import_model():
                definition = self.runtime.directory/'import.Modelfile'
                definition.write_text('FROM '+json.dumps(Path(filename).resolve().as_posix())+'\n', encoding='utf-8')
                result = subprocess.run([str(self.runtime.ollama),'create','notetaker-import-'+uuid4().hex[:10],'-f',str(definition)],
                                        env=self.runtime.model_env, capture_output=True, timeout=1800,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if result.returncode: raise RuntimeError('The selected model could not be imported. Check that it is a supported local Qwen GGUF.')
            self.work(import_model, lambda _:(self.refresh_models(), self.message('Local model imported.')))
            dialog.accept()
        button('Select speech model folder', speech, form)
        button('Use existing Ollama model files', existing, form)
        button('Import local GGUF', gguf, form)
        button('Close', dialog.accept, form); dialog.resize(650, 430); dialog.exec()

    def generate(self):
        if not self.require_lecture() or not self.state: return
        if not self.model.currentText(): self.message('Select or import a local note model first.'); return
        path = '/lectures/'+self.lecture+'/notes/model'
        body = {key:field.toPlainText() for key, field in self.prompts.items()}
        body.update(model=self.model.currentText(), enabled=True, expected_version=(self.state['preference'] or {}).get('version',0))
        self.work(lambda:self.api.post(path, body))

    def load_profile(self):
        def choose(rows):
            if not rows: self.message('No saved profiles yet.'); return
            name, ok = QInputDialog.getItem(self, 'Load profile', 'Profile', [r['name'] for r in rows], editable=False)
            if ok:
                row = next(r for r in rows if r['name'] == name)
                for key, field in self.prompts.items(): field.setPlainText(row[key])
        self.work(lambda:self.api.get('/prompt-profiles'), choose)

    def save_profile(self):
        name, ok = QInputDialog.getText(self, 'Save profile', 'Profile name')
        if ok and name.strip():
            body = {key:field.toPlainText() for key, field in self.prompts.items()}
            body['name'] = name.strip()
            self.work(lambda:self.api.post('/prompt-profiles', body), lambda _:self.message('Profile saved.'))

    def selected(self):
        return (self.state['editing']['selected'] or self.state['revision']) if self.state else None

    def edit_command(self, action, **fields):
        selected = self.selected()
        if not selected: return
        path = '/lectures/'+self.lecture+'/notes/edits'
        body = {'action':action, 'base_id':selected['id'], 'expected_version':self.state['editing']['version'], **fields}
        self.work(lambda:self.api.post(path, body))

    def edit_dialog(self, title, initial, suffix, save):
        lecture = self.lecture; revision = self.selected(); version = self.state['editing']['version']
        path = self.runtime.directory/('draft-'+lecture+'-'+suffix+'.json')
        draft = json.loads(path.read_text('utf-8')) if path.exists() else None
        dialog = QDialog(self); dialog.setWindowTitle(title); layout = QVBoxLayout(dialog)
        text = QPlainTextEdit(); text.setPlainText(draft['text'] if draft else initial); layout.addWidget(text)
        base_id = draft['base_id'] if draft else revision['id']
        version = draft['version'] if draft else version
        def persist():
            temporary = path.with_suffix('.pending')
            with temporary.open('w', encoding='utf-8') as stream:
                json.dump({'base_id':base_id,'version':version,'text':text.toPlainText()}, stream)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,path)
        text.textChanged.connect(persist)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(controls); controls.rejected.connect(dialog.reject)
        def submit():
            persist(); body = {'action':'save','base_id':base_id,'expected_version':version, **save(text.toPlainText())}
            def done(_):
                path.unlink(missing_ok=True); dialog.accept(); self.refresh()
            self.work(lambda:self.api.post('/lectures/'+lecture+'/notes/edits', body), done)
        controls.accepted.connect(submit); dialog.resize(750,500); dialog.exec()

    def edit_passage(self):
        revision = self.selected()
        if not revision: return
        passages = [p for b in revision['content']['blocks'] for p in b['passages']]
        choices = [str(i+1)+'. '+p['text'][:90] for i,p in enumerate(passages)]
        choice, ok = QInputDialog.getItem(self, 'Edit passage', 'Choose a passage', choices, editable=False)
        if ok:
            passage = passages[choices.index(choice)]
            self.edit_dialog('Edit passage', passage['text'], passage['id'], lambda value:{'passages':[{'id':passage['id'],'text':value}]})

    def add_notes(self):
        if self.selected(): self.edit_dialog('My additions', '', 'additions', lambda value:{'additional_text':value})

    def compare(self):
        if not self.state or not self.state['editing']['proposal']: self.message('No new suggestion to compare.'); return
        proposal = self.state['editing']['proposal']
        path = '/lectures/'+self.lecture+'/notes/edits'
        base = {'base_id':self.selected()['id'], 'expected_version':self.state['editing']['version']}
        dialog = QDialog(self); dialog.setWindowTitle('Compare with your saved notes'); layout = QVBoxLayout(dialog)
        panes = QHBoxLayout(); layout.addLayout(panes)
        for revision in [self.selected(),proposal]:
            field = QPlainTextEdit(prose(revision)); field.setReadOnly(True); panes.addWidget(field)
        choices = QHBoxLayout(); layout.addLayout(choices)
        def resolve(action):
            fields = {'proposal_id':proposal['id']}
            if action == 'merge': fields['block_ids'] = [b['id'] for b in proposal['content']['blocks']]
            body = {**base, 'action':action, **fields}
            self.work(lambda:self.api.post(path, body), lambda _:(dialog.accept(),self.refresh()))
        for label, action in [('Keep mine','keep'),('Append suggestion sections','merge'),('Replace with suggestion','replace')]:
            button(label, lambda _=False,a=action:resolve(a), choices).setEnabled(self.state['editing']['proposal_valid'])
        dialog.resize(1100,650); dialog.exec()

    def history(self):
        if not self.require_lecture(): return
        path = '/lectures/'+self.lecture+'/notes/history'
        def choose(data):
            rows = [*data['edits'],*data['generated']]
            labels = [f"{r.get('action','generated')} revision {r['version']} · {r['id'][:8]}" for r in rows]
            label, ok = QInputDialog.getItem(self, 'Restore revision', 'Restore this earlier version as a new saved revision', labels, editable=False)
            if ok: self.edit_command('undo', target_id=rows[labels.index(label)]['id'])
        self.work(lambda:self.api.get(path), choose)

    def source(self):
        revision = self.selected()
        if not revision: return
        sources = list(dict.fromkeys(c['source_id'] for b in revision['content']['blocks'] for p in b['passages'] for c in p['sources']))
        source, ok = QInputDialog.getItem(self, 'Inspect evidence', 'Source version', sources, editable=False)
        if ok:
            path = '/lectures/'+self.lecture+'/sources/'+source
            def display(row):
                dialog = QDialog(self); dialog.setWindowTitle('Source evidence'); layout = QVBoxLayout(dialog)
                text = QPlainTextEdit(row['text']); text.setReadOnly(True); layout.addWidget(text)
                player = QMediaPlayer(dialog); output = QAudioOutput(dialog); player.setAudioOutput(output)
                buffer = QBuffer(dialog)
                if row.get('audio_url'):
                    def play():
                        def ready(data):
                            player.stop(); buffer.close(); buffer.setData(data); buffer.open(QIODevice.OpenModeFlag.ReadOnly)
                            player.setSourceDevice(buffer,QUrl('source.wav')); player.play()
                        self.work(lambda:self.api.get(path+'/audio'), ready)
                    button('Play source audio', play, layout)
                    button('Stop playback', player.stop, layout)
                button('Close', dialog.accept, layout)
                dialog.resize(700,450); dialog.exec(); player.stop()
            self.work(lambda:self.api.get(path), display)

    def correct_transcript(self, item):
        segment = item.data(Qt.ItemDataRole.UserRole); lecture = self.lecture
        text, ok = QInputDialog.getMultiLineText(self, 'Correct transcript', 'Correction preserves the earlier version', segment['text'])
        if ok and text.strip():
            self.work(lambda:self.api.post('/lectures/'+lecture+'/transcript/segments/'+segment['segment_id']+'/corrections',
                                          {'expected_version':segment['revision'],'text':text}))

    def record(self):
        if not self.require_lecture():
            self.message('Select the lecture title under a course before recording. Selecting the course name is not enough.')
            return
        self.tabs.setCurrentIndex(0)
        if self.state and not self.state.get('preference') and self.model.currentText():
            self.generate()
        try: self.recorder.start(self.lecture, self.input.currentData())
        except Exception as exc: self.error(str(exc))

    def stop_recording(self):
        try: self.recorder.stop()
        except Exception as exc: self.error(str(exc))

    def recover(self):
        rows = self.journal.runs()
        if not rows: self.message('No recordings need recovery.'); return
        if self.recorder.source or self.recorder.finishing: self.message('Wait for recording to stop and save before recovery.'); return
        def run():
            for row in rows: self.recorder.recover(row, interrupted=not row['stopped'])
        self.work(run, lambda _:self.message('Saved audio has been reconciled with the library.'))

    def finalize(self):
        if not self.require_lecture(): return
        if self.recorder.source or self.recorder.finishing: self.message('Stop recording and wait for audio verification first.'); return
        path = '/lectures/'+self.lecture+'/finalization'
        lecture = self.lecture
        def display(state):
            dialog = QDialog(self); dialog.setWindowTitle('Final lecture snapshots'); layout = QVBoxLayout(dialog)
            history = QListWidget(); layout.addWidget(history)
            for row in state['history']:
                item = QListWidgetItem(row['status'].replace('_',' ')+' · '+str(row.get('issues',[])))
                item.setData(Qt.ItemDataRole.UserRole,row); history.addItem(item)
            def process(available):
                body = {'expected_cursor':state['cursor'], 'expected_edit_version':state['edit_version'], 'available_only':available}
                self.work(lambda:self.api.post(path,body), lambda _:(dialog.accept(),self.message('Final processing requested. Open Finalize to review progress.')))
            button('Finish all processing', lambda:process(False), layout)
            button('Freeze available results as incomplete', lambda:process(True), layout)
            def export_snapshot():
                if not history.currentItem(): return
                row = history.currentItem().data(Qt.ItemDataRole.UserRole)
                if not row.get('snapshot_id'): self.message('This request has no completed snapshot yet.'); return
                filename, _ = QFileDialog.getSaveFileName(dialog,'Export immutable snapshot','Final lecture.md','Markdown (*.md)')
                if filename:
                    endpoint = '/lectures/'+lecture+'/final-snapshots/'+row['snapshot_id']+'/export'
                    self.work(lambda:Path(filename).write_bytes(self.api.get(endpoint)),lambda _:self.message('Immutable snapshot exported.'))
            button('Export selected snapshot',export_snapshot,layout)
            button('Close',dialog.accept,layout); dialog.resize(700,400); dialog.exec()
        self.work(lambda:self.api.get(path),display)

    def export(self):
        revision = self.selected()
        if not revision: return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export selected saved notes', 'Study notes.md', 'Markdown (*.md)')
        if filename:
            path = '/lectures/'+self.lecture+'/notes/'+('edits/' if revision.get('student') else 'revisions/')+revision['id']+'/export'
            self.work(lambda:Path(filename).write_bytes(self.api.get(path)), lambda _:self.message('Selected saved notes exported.'))

    def closeEvent(self, event):
        if self.recorder.source or self.recorder.starting or self.recorder.finishing:
            self.error('Stop and save your recording before closing the application.'); event.ignore(); return
        self.timer.stop()
        self.cleanup_timer.stop()
        self.model_timer.stop()
        for stream in self.streams: stream.stop.set()
        event.accept()
