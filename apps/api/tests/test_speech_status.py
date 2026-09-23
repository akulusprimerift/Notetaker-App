import json
import time
from types import SimpleNamespace

from notetaker.speech_status import speech_status, start_status


def test_readiness_requires_current_worker_and_compatible_load(tmp_path):
    model = tmp_path / 'model'
    model.mkdir()
    settings = SimpleNamespace(speech_model_path=str(model),
        speech_status_path=str(tmp_path / 'status.json'), speech_status_session='current')
    assert speech_status(settings)['state'] == 'missing'
    for name in ('model.bin', 'config.json', 'tokenizer.json'):
        (model / name).write_text('fixture')
    assert speech_status(settings)['state'] == 'offline'
    record = {'session': 'current', 'model': str(model), 'updated': time.time(), 'ready': True}
    def save(**changes):
        (tmp_path / 'status.json').write_text(json.dumps({**record, **changes}))
        return speech_status(settings)['state']
    assert save() == 'ready'
    assert save(session='previous-launch') == 'offline'
    assert save(model='other-model') == 'offline'
    assert save(updated=time.time()-20) == 'offline'
    assert save(updated=time.time()+30) == 'offline'
    assert save(ready=False) == 'loading'
    assert save(ready=False, failed=True) == 'failed'
    (tmp_path / 'status.json').write_text('{partial')
    assert speech_status(settings)['state'] == 'offline'
    settings.speech_status_path = ''
    assert speech_status(settings)['state'] == 'selected'


def test_worker_publishes_only_loaded_readiness(tmp_path):
    settings = SimpleNamespace(speech_model_path='fixture',
        speech_status_path=str(tmp_path / 'status.json'), speech_status_session='current')
    provider = SimpleNamespace(model=object(), metadata={})
    stopped = start_status(settings, provider)
    try:
        deadline = time.monotonic() + 5
        while not (tmp_path / 'status.json').exists() and time.monotonic() < deadline:
            time.sleep(.02)
        record = json.loads((tmp_path / 'status.json').read_text())
        assert record['ready'] is True
        assert record['session'] == 'current'
    finally:
        stopped.set()
