"""Native connection setup. Keys stay in Windows-protected private storage."""
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QLineEdit, QLabel,
    QPushButton, QFileDialog, QHBoxLayout)
from notetaker.provider_connections import Connections, PROVIDERS
from notetaker.subscription_notes import sign_in, sign_out
from notetaker.cloud_notes import NoteProviders


def connection_dialog(window):
    dialog = QDialog(window); dialog.setWindowTitle('AI connections'); form = QFormLayout(dialog)
    store = Connections(str(window.runtime.directory/'connections'))
    provider = QComboBox()
    for label, ident in zip(['OpenAI API', 'Claude API', 'ChatGPT subscription · Codex', 'Claude subscription · Claude Code'], PROVIDERS):
        provider.addItem(label, ident)
    form.addRow('Connection', provider)
    model = QLineEdit(); model.setPlaceholderText('Model ID available on your account')
    form.addRow('Model', model)
    key = QLineEdit(); key.setEchoMode(QLineEdit.EchoMode.Password)
    form.addRow('API key', key)
    executable = QLineEdit(); executable.setReadOnly(True)
    form.addRow('Official client', executable)
    browse = QPushButton('Select installed client (.exe)'); form.addRow(browse)
    info = QLabel(''); info.setWordWrap(True); form.addRow(info)
    actions = QHBoxLayout(); form.addRow(actions)
    save = QPushButton('Save connection'); login = QPushButton('Sign in with subscription')
    remove = QPushButton('Disconnect'); test = QPushButton('Test with sample text'); logout = QPushButton('Sign out')
    for button in (save, login, remove, logout, test): actions.addWidget(button)

    def load():
        ident = provider.currentData(); subscription = ident in ('chatgpt', 'claude-subscription')
        key.clear(); model.clear(); executable.clear()
        key.setEnabled(not subscription); browse.setEnabled(subscription); login.setEnabled(subscription)
        logout.setEnabled(subscription)
        try: row = store.read(ident)
        except (ValueError, OSError): row = None
        if row:
            model.setText(row['model']); executable.setText(row['executable'])
        key.setPlaceholderText('Enter a new key to save or replace this connection')
        info.setText(('Uses your subscription through the installed official client. Sign-in opens your system browser. '
            'Model access and usage limits depend on your plan. Claude third-party subscription availability is provider-controlled. '
            'Notetaker keeps a separate client sign-in; disconnect removes its use from Notetaker.' if subscription else
            'Uses a separately billed provider API key, protected by your Windows account. Chat subscriptions do not supply API credits.') +
            '\nCloud note generation sends the selected lecture transcript, selected material text and note prompts. Audio transcription stays local. '
            'Choose this connection in Note preferences and confirm for each lecture. Testing sends a short synthetic example and may consume usage.')

    def choose_executable():
        filename, _ = QFileDialog.getOpenFileName(dialog, 'Select official Codex or Claude Code client', '', 'Windows executable (*.exe)')
        if filename: executable.setText(filename)

    def save_connection():
        try:
            store.save(provider.currentData(), model.text().strip(), key.text().strip(), executable.text())
            key.clear(); window.refresh_models(); window.message('Connection saved. Select it in Note preferences for a lecture.')
            return True
        except (OSError, ValueError) as exc:
            window.error(str(exc)); return False

    def login_connection():
        if not save_connection(): return
        ident, path = provider.currentData(), executable.text()
        window.message('Finish signing in in your system browser. This may take up to three minutes.')
        window.work(lambda:sign_in(ident, path, str(store.directory)),
                    lambda _:window.message('Provider sign-in finished. Select this model in Note preferences.'))

    def disconnect():
        try:
            store.remove(provider.currentData()); window.refresh_models(); load()
            window.message('Disconnected from Notetaker. Saved notes remain. Provider-client sign-in is retained; sign out in that client to revoke it.')
        except (OSError, ValueError) as exc: window.error(str(exc))

    def test_connection():
        ident = provider.currentData()
        try: row = store.read(ident)
        except (OSError, ValueError): row = None
        if not row: window.error('Save a connection first.'); return
        settings = SimpleNamespace(standalone=True, provider_directory=str(store.directory), ollama_url='http://127.0.0.1:11434')
        adapter = NoteProviders(settings)
        pref = SimpleNamespace(model=ident+'/'+row['model'], model_digest=row['id'])
        evidence = {'source_snapshot_id':'connection-test', 'settings_version':1, 'allow_ai_explanations':False,
            'sources':[{'id':'sample', 'text':'Water evaporates into vapor. Cooling vapor condenses into liquid water.'}]}
        def run():
            try: return adapter.generate(evidence, pref)
            except Exception: raise ValueError('Connection test failed. Check sign-in, model access, key and remaining provider usage.') from None
        window.work(run, lambda _:window.message('Connection test passed: the provider returned validated notes from sample text.'))

    def logout_connection():
        ident, path = provider.currentData(), executable.text()
        if not path: window.error('Select the official client first.'); return
        def run():
            sign_out(ident, path, str(store.directory)); store.remove(ident)
        window.work(run, lambda _:(window.refresh_models(), window.message('Signed out of the Notetaker subscription connection.')))

    provider.currentIndexChanged.connect(load); browse.clicked.connect(choose_executable)
    save.clicked.connect(save_connection); login.clicked.connect(login_connection)
    remove.clicked.connect(disconnect); test.clicked.connect(test_connection)
    logout.clicked.connect(logout_connection)
    load(); dialog.resize(780,440); dialog.exec()
