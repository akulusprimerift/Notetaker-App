"""Explicit Windows-only provider connections; secrets never enter lecture history."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
from uuid import uuid4

PROVIDERS = ('openai', 'anthropic', 'chatgpt', 'claude-subscription')


def protect(data, decrypt=False):
    if os.name != 'nt':
        raise ValueError('Provider connections require Windows protected storage.')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ValueError('Windows could not unlock this provider connection. Connect again using this Windows account.')
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(result.data)


class Connections:
    def __init__(self, directory):
        self.directory = Path(directory) if directory else None

    def path(self, provider):
        if not self.directory or provider not in PROVIDERS:
            raise ValueError('Provider connections are unavailable in this profile.')
        return self.directory / (provider + '.connection')

    def read(self, provider):
        path = self.path(provider)
        if not path.exists():
            return None
        if path.stat().st_size > 32000:
            raise ValueError('Provider connection is invalid. Connect again.')
        return json.loads(protect(path.read_bytes(), decrypt=True))

    def save(self, provider, model, api_key='', executable=''):
        path = self.path(provider)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,119}', model):
            raise ValueError('Enter a valid model ID from your provider.')
        if provider in ('openai', 'anthropic'):
            if not api_key or len(api_key) > 8192 or any(c.isspace() for c in api_key):
                raise ValueError('Enter an API key without spaces.')
        else:
            target = Path(executable)
            if not target.is_absolute() or target.suffix.lower() != '.exe' or not target.is_file():
                raise ValueError('Select the installed official provider executable (.exe).')
        row = {'model':model, 'api_key':api_key, 'executable':executable, 'id':str(uuid4())}
        encrypted = protect(json.dumps(row).encode())
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.' + uuid4().hex + '.pending')
        try:
            with temporary.open('xb') as stream:
                stream.write(encrypted); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def remove(self, provider):
        self.path(provider).unlink(missing_ok=True)

    def inventory(self):
        if not self.directory:
            return []
        rows = []
        for provider in PROVIDERS:
            try:
                row = self.read(provider)
                if row:
                    rows.append({'name':provider+'/'+row['model'], 'digest':row['id'], 'size':0, 'provider':provider})
            except (OSError, ValueError, KeyError):
                continue
        return rows
