PALETTES = {
    'Slate': ('#e0e1dd', '#f2f3f1', '#1b263b', '#415a77', '#778da9', '#8e9aaf'),
    'Midnight': ('#090d17', '#121b2d', '#f4f4f7', '#bd9df4', '#ffa45c', '#415a77'),
}


def stylesheet(name):
    bg, surface, ink, accent, focus, border = PALETTES.get(name, PALETTES['Slate'])
    return f'''
    QWidget {{ background: {bg}; color: {ink}; font: 11pt "Segoe UI"; }}
    QMainWindow {{ background: {bg}; }}
    QLabel#heading {{ font-size: 24pt; font-weight: 600; padding: 12px 0; }}
    QLabel#subheading {{ font-size: 15pt; font-weight: 600; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QTreeWidget, QComboBox {{
        background: {surface}; border: 1px solid {border}; border-radius: 6px; padding: 8px;
        selection-background-color: {accent}; selection-color: {bg};
    }}
    QPushButton {{ background: {surface}; border: 1px solid {border}; border-radius: 6px; padding: 8px 14px; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton:focus, QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 2px solid {focus}; }}
    QPushButton:disabled {{ color: {border}; }}
    QTabBar::tab {{ padding: 10px 18px; }}
    QTabBar::tab:selected {{ border-bottom: 3px solid {accent}; }}
    QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 12px; padding-top: 16px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; }}
    QStatusBar {{ padding: 4px; }}
    '''
