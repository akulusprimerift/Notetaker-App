"""Native diagram reader using Qt SVG, without a browser engine."""
from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget
from notetaker.visual_notes import diagram_svg, diagram_description, diagram_stale


class VisualNotes(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setAccessibleName('Source-linked visual notes')
        self.revision_id = None
        self.show_revision(None)

    def show_revision(self, revision):
        ident = revision['id'] if revision else None
        if ident is not None and ident == self.revision_id:
            return
        self.revision_id = ident
        position = self.verticalScrollBar().value()
        page = QWidget(); layout = QVBoxLayout(page)

        def label(text):
            field = QLabel(text)
            field.setTextFormat(Qt.TextFormat.PlainText)
            field.setWordWrap(True)
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
            layout.addWidget(field)

        label('AI-created schematics from cited lecture text. These are not captured slide or board images. Check scientific accuracy against the sources.')
        blocks = [b for b in revision['content']['blocks'] if b.get('diagram')] if revision else []
        if not blocks:
            label('Diagrams appear here when the lecture supports a visual explanation. In Note preferences, ask for process diagrams, cycles or concept maps, then apply and write notes.')
        for block in blocks:
            label(block['topic'])
            diagram = block['diagram']
            view = QSvgWidget()
            view.load(QByteArray(diagram_svg(diagram).encode('utf-8')))
            view.setMinimumHeight(max(360, len(diagram['nodes']) * 50))
            view.setAccessibleName(diagram['caption'])
            layout.addWidget(view)
            label(diagram['caption'])
            if diagram_stale(block):
                label('Review diagram: this section has student changes; the original diagram is retained.')
            label(diagram_description(diagram))
            for passage in block['passages']:
                label(passage['text'])
            label('Source versions: ' + ', '.join(dict.fromkeys(c['source_id'] for p in block['passages'] for c in p['sources'])))
        layout.addStretch()
        old = self.takeWidget()
        self.setWidget(page)
        if old:
            old.deleteLater()
        self.verticalScrollBar().setValue(position)
        QTimer.singleShot(0, lambda:self.verticalScrollBar().setValue(position) if self.revision_id == ident else None)
