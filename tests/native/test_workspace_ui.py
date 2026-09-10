import time
from types import SimpleNamespace
from uuid import uuid4
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
from test_workspace import setup
from test_capture import capture
from test_transcription import speech
from test_notes import notes, correction, FakeNotes
from test_note_edits import generated
from notetaker.note_worker import plan, claim, execute
from notetaker_native.window import Window


def until(app, condition):
    deadline = time.monotonic()+10
    while not condition() and time.monotonic()<deadline:
        app.processEvents(); time.sleep(.01)
    assert condition()


def test_native_saved_edits_survive_proposal_and_course_deletion(notes, tmp_path, monkeypatch):
    backend, client, headers, path, _ = notes
    generated(backend,client,path)
    app = QApplication.instance() or QApplication([])
    class Api:
        def get(self, path):
            result = client.get(path); result.raise_for_status(); return result.json()
        def post(self, path, body=None):
            result = client.post(path,json=body or {},headers={**headers,'idempotency-key':str(uuid4())})
            result.raise_for_status(); return result.json()
    runtime = SimpleNamespace(directory=tmp_path,config={},save_config=lambda:None,
                              detected={'ollama':[],'gguf':[],'speech':[]})
    window = Window(Api(),runtime)
    window.show()
    try:
        until(app,lambda:window.tree.topLevelItemCount()==1)
        item = window.tree.topLevelItem(0).child(0)
        # Avoid starting HTTP SSE on the in-process test transport. Production
        # streaming is independently exercised by the native stream test.
        window.course = item.data(0,Qt.ItemDataRole.UserRole)[1]['course_id']
        window.lecture = path.split('/')[-1]; window.refresh()
        until(app,lambda:window.state is not None)
        window.edit_command('save',additional_text='My protected native addition.')
        until(app,lambda:window.state['editing']['version']==1)
        assert 'My protected native addition.' in window.notes.toPlainText()
        correction(client,headers,path); plan(backend.state.sessions)
        chosen = claim(backend.state.sessions)
        assert chosen and execute(backend.state.sessions,FakeNotes(),chosen,heartbeat=False)
        window.refresh()
        until(app,lambda:window.state['editing']['proposal'] is not None)
        def keep():
            dialog = app.activeModalWidget()
            next(b for b in dialog.findChildren(QPushButton) if b.text()=='Keep mine').click()
        QTimer.singleShot(100,keep)
        window.compare()
        until(app,lambda:window.state['editing']['version']==2)
        assert 'My protected native addition.' in window.notes.toPlainText()
        window.change_theme('Midnight')
        assert runtime.config['theme']=='Midnight'
        monkeypatch.setattr(QMessageBox,'question',lambda *_:QMessageBox.StandardButton.Yes)
        sibling = window.api.post('/courses/'+window.course+'/lectures', {'title':'Keep this lecture'})
        window.delete_lecture()
        until(app,lambda:window.lecture is None)
        remaining = client.get('/courses/'+window.course+'/lectures').json()
        assert [row['id'] for row in remaining] == [sibling['id']]
        assert client.get(path+'/transcript').status_code == 404
        window.delete_course()
        until(app,lambda:window.course is None)
        assert client.get('/courses').json()==[]
    finally:
        window.close()
        until(app,lambda:not window.polling and not window.cleaning)
