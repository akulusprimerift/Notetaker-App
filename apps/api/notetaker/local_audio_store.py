"""Explicit standalone private storage with verified, immutable atomic objects."""
import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4


class LocalAudioStore:
    available = True

    def __init__(self, directory):
        self.root = Path(directory).resolve()

    def ready(self):
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key):
        if not key or not re.fullmatch(r'[A-Za-z0-9_./-]+', key) or any(p in ('', '.', '..') for p in key.split('/')):
            raise ValueError('invalid_object_key')
        path = self.root.joinpath(*key.split('/'))
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('invalid_object_key')
        return path

    def read(self, key):
        with self.path(key).open('rb') as stream:
            return stream.read(8 * 1024 * 1024 + 1)

    def write_verified(self, key, data, checksum):
        if hashlib.sha256(data).hexdigest() != checksum:
            raise ValueError('audio_checksum_mismatch')
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.pending-' + uuid4().hex)
        try:
            with temporary.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                pass
            if self.read(key) != data:
                raise RuntimeError('audio_readback_mismatch')
        finally:
            temporary.unlink(missing_ok=True)

    def list_keys(self, prefix):
        self.ready()
        base = self.path(prefix.rstrip('/'))
        if not base.exists():
            return []
        return [p.relative_to(self.root).as_posix() for p in base.rglob('*')
                if p.is_file() and p.resolve().is_relative_to(self.root)]

    def delete_verified(self, key):
        target = self.path(key)
        target.unlink(missing_ok=True)
        if target.exists():
            raise RuntimeError('object_still_present')
