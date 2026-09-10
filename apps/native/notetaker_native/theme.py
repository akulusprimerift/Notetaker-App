PALETTES = {
    'Slate': ('#f5f6f8', '#ffffff', '#24344b', '#415a77', '#778da9', '#dce2e9'),
    'Midnight': ('#090d17', '#121b2d', '#f4f4f7', '#bd9df4', '#ffa45c', '#415a77'),
}


def stylesheet(name):
    bg, surface, ink, accent, focus, border = PALETTES.get(name, PALETTES['Slate'])
    return f'''
    QWidget {{ background: {bg}; color: {ink}; font: 11pt "Segoe UI"; }}
    QMainWindow {{ background: {bg}; }}
    QLabel#heading {{ font-size: 24pt; font-weight: 600; padding: 12px 0; }}
    QLabel#subheading {{ font-size: 15pt; font-weight: 600; }}
    QLabel {{ background: transparent; }}
    QWidget#library {{ background: {surface}; border-radius: 12px; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QTreeWidget, QComboBox {{
        background: {surface}; border: 1px solid {border}; border-radius: 6px; padding: 8px;
        selection-background-color: {accent}; selection-color: {bg};
    }}
    QPushButton {{ background: {surface}; border: 1px solid {border}; border-radius: 6px; padding: 8px 14px; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton:focus, QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 2px solid {focus}; }}
    QPushButton:disabled {{ color: {border}; }}
    QPushButton#primary {{ background: {accent}; color: {surface}; font-weight: 600; border: 0; }}
    QPushButton#primary:disabled {{ background: {border}; color: {ink}; }}
    QPushButton#primary[recording="true"] {{ background: #a83d35; color: #ffffff; font-weight: 700; }}
    QTreeWidget {{ border: 0; background: {surface}; }}
    QTreeWidget::item {{ padding: 10px 4px; margin: 2px 0; }}
    QTreeWidget::item:selected {{ background: {bg}; color: {ink}; border-radius: 6px; }}
    QPlainTextEdit {{ padding: 16px; font-size: 12pt; }}
    QListWidget::item {{ padding: 12px 6px; }}
    QTabWidget::pane {{ border: 0; background: {surface}; }}
    QTabBar::tab {{ padding: 10px 18px; border: 0; background: transparent; }}
    QTabBar::tab:selected {{ border-bottom: 3px solid {accent}; }}
    QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 12px; padding-top: 16px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; }}
    QStatusBar {{ padding: 4px; }}
    QSplitter::handle {{ background: {bg}; width: 12px; height: 12px; }}
    QProgressBar {{ border: 1px solid {border}; border-radius: 5px; background: {surface}; max-height: 12px; }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
    QScrollBar:vertical {{ background: {bg}; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {border}; min-height: 30px; border-radius: 5px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    '''
