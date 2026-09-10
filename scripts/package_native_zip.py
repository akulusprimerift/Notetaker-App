"""Package the native folder with bounded-memory compression and atomic publication."""
from pathlib import Path
import sys
import zipfile

bundle, destination = (Path(value).resolve() for value in sys.argv[1:])
temporary = destination.with_suffix('.pending.zip')
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
    for path in sorted(bundle.rglob('*')):
        if path.is_file(): archive.write(path, path.relative_to(bundle))
temporary.replace(destination)
