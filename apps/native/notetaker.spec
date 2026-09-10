# Build with the pinned native lock; neither executable imports a browser engine.
from pathlib import Path
import os
import sys
import hashlib
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

root = Path(SPECPATH).parents[1]
# Do not resolve DLLs from unrelated developer applications on PATH.
os.environ['PATH'] = os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),
    os.environ['SystemRoot'], str(Path(sys.base_prefix)), str(root/'.venv/Scripts')])
paths = [str(root/'apps/api'), str(root/'apps/native')]
data = [(str(root/'contracts/ai'), 'contracts/ai'), (str(root/'prompts'), 'prompts'),
        (str(root/'apps/api/migrations'), 'apps/api/migrations'),
        (str(root/'.local/native-vendor/ollama'), 'vendor/ollama'),
        (str(root/'.local/native-vendor/notices'), 'third-party-notices')]
speech = root/'.local/models/faster-whisper-small.en'
speech_hashes = {
    'model.bin': '62b2a45b05ee59acb4a5341b33ee35e041395d378d418a18acfe4c9e768ee37a',
    'config.json': '666a9605530ac1f61fa8177f3702b4dacec9966749e42610839fcc32661d5fae',
    'tokenizer.json': '929c5252409436dce1b38a75d1abbcb5e132d170d8e324e4e04ed915fa2d22df',
    'vocabulary.txt': 'ff77588746d3a2595d32ab5b69ffd7b95ce2441ac57533cb66fc3eb575a115cf',
}
for name, expected in speech_hashes.items():
    if not (speech/name).is_file():
        raise RuntimeError('Bundled speech model missing. Run scripts/Prepare-NativeSpeech.ps1 first.')
    with (speech/name).open('rb') as model_file:
        if hashlib.file_digest(model_file, 'sha256').hexdigest() != expected:
            raise RuntimeError('Bundled speech model checksum mismatch: '+name)
    data.append((str(speech/name), 'vendor/speech/faster-whisper-small.en'))
for folder in ['apps/native', 'apps/api/notetaker']:
    data += [(str(file), 'application-source/'+file.parent.relative_to(root).as_posix())
             for file in (root/folder).rglob('*.py') if '__pycache__' not in file.parts]
data += [(str(root/'apps/native/notetaker.spec'), 'application-source/apps/native'),
         (str(root/'docs/native-third-party.md'), 'third-party-notices')]
for package in ['faster_whisper', 'tokenizers', 'ctranslate2']:
    data += collect_data_files(package)
for package in ['uvicorn', 'faster-whisper', 'huggingface-hub']:
    data += copy_metadata(package)
excluded = ['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
            'PySide6.QtWebView', 'PySide6.QtQuick', 'PySide6.QtQml', 'torch', 'tensorflow',
            'matplotlib', 'pytest', 'playwright', 'notetaker.verify_services', 'notetaker.verify_speech']
service = Analysis([str(root/'apps/native/service.py')], pathex=paths, datas=data,
    binaries=collect_dynamic_libs('ctranslate2'),
    hiddenimports=collect_submodules('uvicorn')+['notetaker.main', 'notetaker.material_parser',
        'sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.postgresql.psycopg'], excludes=excluded)
service_pyz = PYZ(service.pure)
service_exe = EXE(service_pyz, service.scripts, [], exclude_binaries=True, name='NotetakerService', console=True)
gui = Analysis([str(root/'apps/native/main.py')], pathex=paths, datas=[], binaries=[],
               hiddenimports=['notetaker_native.smoke'], excludes=excluded)
# Qt uses the Windows system ICU API, whose unversioned symbols differ from
# third-party ICU builds that can appear on a developer's PATH (e.g. Poppler).
gui.binaries = [entry for entry in gui.binaries if not Path(entry[0]).name.lower().startswith(('icuuc', 'icudt'))]
gui_pyz = PYZ(gui.pure)
gui_exe = EXE(gui_pyz, gui.scripts, [], exclude_binaries=True, name='Notetaker', console=os.environ.get('NOTETAKER_DEBUG_CONSOLE') == '1')
bundle = COLLECT(gui_exe, service_exe, gui.binaries, gui.datas, service.binaries, service.datas,
                 strip=False, upx=False, name='Notetaker')
