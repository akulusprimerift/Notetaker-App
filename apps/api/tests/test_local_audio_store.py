import hashlib
import pytest
from notetaker.local_audio_store import LocalAudioStore
from notetaker.config import Settings
from notetaker.audio_store import AudioStore


def test_standalone_objects_verify_retry_and_reject_overwrite(tmp_path):
    store = AudioStore(Settings(standalone=True, database_url='sqlite:///'+str(tmp_path/'data.db'), audio_directory=str(tmp_path/'audio')))
    assert isinstance(store, LocalAudioStore)
    data = b'preserved synthetic audio'
    key = 'lecture/run/chunk.wav'
    store.write_verified(key, data, hashlib.sha256(data).hexdigest())
    store.write_verified(key, data, hashlib.sha256(data).hexdigest())
    with pytest.raises(RuntimeError, match='readback'):
        store.write_verified(key, b'other', hashlib.sha256(b'other').hexdigest())
    assert store.read(key) == data
    assert store.list_keys('lecture/') == [key]
    store.delete_verified(key)
    store.delete_verified(key)
    assert store.list_keys('lecture/') == []


@pytest.mark.parametrize('key', ['../outside', '/absolute', 'a/../../b', 'C:/outside', 'a//b'])
def test_standalone_storage_rejects_path_escape(tmp_path, key):
    with pytest.raises(ValueError):
        LocalAudioStore(tmp_path).read(key)
