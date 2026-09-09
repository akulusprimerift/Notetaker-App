"""Opt-in synthetic packaged smoke. Never requests a microphone device."""
import base64
import json
from pathlib import Path
import secrets
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem
from .client import background


def run(window, destination, app):
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    report = {'browser_engine':False, 'microphone_accessed':False}
    def verify():
        api = window.api
        model_inventory = api.get('/note-models')
        course = api.post('/courses', {'name':'Synthetic native smoke'})
        lecture = api.post('/courses/'+course['id']+'/lectures', {'title':'Synthetic recording'})
        path = '/lectures/'+lecture['id']
        api.post(path+'/materials', {'name':'curriculum.txt','kind':'curriculum','expected_count':0,
                                    'data':base64.b64encode(b'Binary search halves the search interval.').decode()})
        assert len(api.get(path+'/materials')) == 1
        grant = secrets.token_urlsafe(32)
        state = api.get(path+'/capture')
        manifest = api.post(path+'/capture-runs', {'sample_rate':16000,'grant':grant,'expected_capture_epoch':state['capture_epoch']})
        window.journal.start(lecture['id'], manifest, grant)
        identity = window.journal.append(manifest['id'], b'\0\0'*16000)
        window.journal.stop(manifest['id'])
        run = {**manifest, 'lecture':lecture['id'], 'grant':grant}
        window.recorder.recover(run, interrupted=False)
        assert not window.journal.pending(manifest['id'])
        saved = api.get(path+'/capture-runs/'+manifest['id']+'/manifest')
        assert saved['chunks'][0]['sha256'] == identity['sha256']
        report.update(material_upload=True, synthetic_capture=True, verified_audio=True, course_id=course['id'],
                      detected_note_models=len(model_inventory.get('models', [])),
                      note_models_available=model_inventory.get('available', False))
        return course, lecture
    def shown(rows):
        course, lecture = rows
        window.tree.blockSignals(True); window.tree.clear()
        parent = QTreeWidgetItem([course['name']]); parent.setData(0,Qt.ItemDataRole.UserRole,('course',course))
        child = QTreeWidgetItem([lecture['title']]); child.setData(0,Qt.ItemDataRole.UserRole,('lecture',lecture))
        parent.addChild(child); window.tree.addTopLevelItem(parent); parent.setExpanded(True)
        window.tree.setCurrentItem(child); window.tree.blockSignals(False)
        window.course = course['id']; window.lecture = lecture['id']
        window.title.setText('Synthetic lecture · native Windows')
        window.notes.setPlainText('Binary search\n\nEach step halves the search interval. The transcript and uploaded curriculum remain separate sources.')
        window.review_text.setText('Worth reviewing\nSynthetic notice for dismissal verification.')
        window.review.show(); window.show_review.hide()
        window.change_theme('Slate'); app.processEvents(); window.grab().save(str(destination/'slate.png'))
        window.dismiss_review(); assert window.review.isHidden()
        window.restore_review(); assert not window.review.isHidden()
        window.change_theme('Midnight'); app.processEvents(); window.grab().save(str(destination/'midnight.png'))
        assert not any('webengine' in name.lower() for name in sys.modules)
        report.update(native_widgets=True, themes=True, review_dismissal=True)
        (destination/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        window.close(); app.quit()
    def failed(text):
        report['error'] = text
        (destination/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        app.exit(1)
    background(verify, shown, failed)
