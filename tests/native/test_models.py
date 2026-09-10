from pathlib import Path
from notetaker_native import runtime


def test_fresh_library_uses_bundled_speech_without_user_cache(tmp_path, monkeypatch):
    bundle = tmp_path/'bundle'
    model = bundle/'vendor/speech/faster-whisper-small.en'
    model.mkdir(parents=True)
    (model/'model.bin').write_bytes(b'synthetic model marker')
    (model/'config.json').write_text('{}')
    monkeypatch.setattr(runtime,'resource_root',lambda:bundle)
    monkeypatch.setattr(Path,'home',lambda:tmp_path/'empty-home')
    instance = runtime.Runtime(tmp_path/'library')
    try:
        assert instance.config['speech_model'] == str(model)
    finally:
        instance.close()
