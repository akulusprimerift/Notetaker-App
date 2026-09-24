from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH).parent
datas = [(str(root / 'apps/api/migrations'), 'apps/api/migrations'),
         (str(root / 'contracts/ai'), 'contracts/ai'), (str(root / 'prompts'), 'prompts')]
binaries = []
hidden = collect_submodules('notetaker') + ['sqlalchemy.dialects.postgresql.psycopg']
for package in ['faster_whisper', 'ctranslate2', 'tokenizers', 'av', 'docx', 'pptx']:
    package_data, package_bins, package_imports = collect_all(package)
    datas += package_data
    binaries += package_bins
    hidden += package_imports
a = Analysis([str(root / 'apps/api/windows_service.py')], pathex=[str(root / 'apps/api')],
    binaries=binaries, datas=datas, hiddenimports=hidden, excludes=['PySide6', 'PyQt6', 'tkinter'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='NotetakerService', console=True)
coll = COLLECT(exe, a.binaries, a.datas, name='NotetakerService')
