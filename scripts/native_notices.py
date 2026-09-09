"""Collect redistribution notices from pinned runtime wheels without model files."""
from importlib import metadata
from pathlib import Path
import re
import shutil

root = Path(__file__).resolve().parents[1]
destination = root/'.local/native-vendor/notices'
destination.mkdir(parents=True, exist_ok=True)
names = re.findall(r'^([a-zA-Z0-9_-]+)==', (root/'apps/api/requirements-native.lock').read_text(), re.MULTILINE)
inventory = []
for name in names:
    try:
        package = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        continue  # Universal lock entries for other operating systems are not bundled.
    folder = destination/name
    folder.mkdir(exist_ok=True)
    (folder/'METADATA.txt').write_text(package.read_text('METADATA') or '', encoding='utf-8')
    for file in package.files or []:
        if re.search(r'(^|/)(licenses?|copying|notice)([./_-]|$)', str(file), re.IGNORECASE):
            source = Path(package.locate_file(file))
            if source.is_file():
                target = folder/str(file).replace('/', '_')
                shutil.copyfile(source, target)
    inventory.append(name+' '+package.version)
(destination/'DEPENDENCIES.txt').write_text('\n'.join(inventory)+'\n', encoding='utf-8')
