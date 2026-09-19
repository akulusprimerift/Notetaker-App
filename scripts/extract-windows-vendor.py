"""Extract only the declared server/CPU runtime components from pinned archives."""
from pathlib import Path, PurePosixPath
import sys
import zipfile

archive, destination, component = sys.argv[1:]
root = Path(destination).resolve()
with zipfile.ZipFile(archive) as bundle:
    for entry in bundle.infolist():
        name = PurePosixPath(entry.filename)
        if name.is_absolute() or '..' in name.parts or '\\' in entry.filename:
            raise ValueError('Unsafe archive entry')
        parts = name.parts
        if component == 'postgres':
            if not parts or parts[0] != 'pgsql':
                continue
            parts = parts[1:]
            if not parts or parts[0] not in ('bin', 'lib', 'share', 'server_license.txt', 'commandlinetools_3rd_party_licenses.txt'):
                continue
        elif component == 'ollama':
            if any(part in ('cuda_v12', 'cuda_v13', 'vulkan') for part in parts):
                continue
        target = root.joinpath(*parts)
        if not target.resolve().is_relative_to(root):
            raise ValueError('Unsafe archive entry')
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, target.open('xb') as output:
                import shutil
                shutil.copyfileobj(source, output)
