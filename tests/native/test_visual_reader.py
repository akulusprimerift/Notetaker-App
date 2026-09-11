from pathlib import Path
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtSvgWidgets import QSvgWidget
from notetaker_native.visual_notes import VisualNotes


def test_native_diagram_reader_and_clear(tmp_path):
    app = QApplication.instance() or QApplication([])
    widget = VisualNotes(); widget.resize(1050,800); widget.show()
    revision = {'id':'visual', 'content':{'blocks':[{'topic':'ATP hydrolysis',
        'diagram':{'caption':'Energy transfer described in the lecture',
            'nodes':[{'id':'a','label':'ATP + water'}, {'id':'b','label':'ADP + phosphate'}],
            'edges':[{'from':'a','to':'b','label':'releases energy'}]},
        'passages':[{'text':'ATP hydrolysis releases energy.', 'sources':[{'source_id':'synthetic-biology'}]}]}]}}
    widget.show_revision(revision); app.processEvents()
    assert len(widget.findChildren(QSvgWidget)) == 1
    assert any('ATP + water → ADP + phosphate' in x.text() for x in widget.findChildren(QLabel))
    Path('.local').mkdir(exist_ok=True)
    widget.grab().save('.local/visual-notes-preview.png')
    widget.show_revision(None); app.processEvents()
    assert not widget.widget().findChildren(QSvgWidget)
    widget.close()
