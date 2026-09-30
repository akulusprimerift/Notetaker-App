import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from notetaker.config import Settings
from notetaker.note_provider import OllamaNotes
from notetaker.speech_provider import WhisperProvider
from test_capture import chunk


@pytest.mark.parametrize('live,beam', [(True, 1), (False, 5)])
def test_live_decode_is_fast_and_saved_decode_retains_beam(monkeypatch, live, beam):
    seen = {}
    provider = WhisperProvider(Settings())
    def transcribe(audio, **options):
        seen.update(options)
        return iter([]), None
    provider.model = SimpleNamespace(transcribe=transcribe)
    provider.metadata = {}
    monkeypatch.setattr(provider, 'load', lambda: None)
    window = SimpleNamespace(live=live, core_start=0, core_end=960,
        context_start=0, context_end=960)
    audio, _ = chunk({'id': 'test', 'capture_epoch': 1}, amplitude=0)
    result = provider.transcribe(audio, window, 48000)
    assert seen['beam_size'] == result['metadata']['beam_size'] == beam
    assert seen['word_timestamps'] and seen['vad_filter']
    assert result['outcome'] == 'silence'


def test_live_beam_override_is_bounded():
    assert Settings(speech_live_beam_size=5).speech_live_beam_size == 5
    with pytest.raises(ValidationError):
        Settings(speech_live_beam_size=0)


def test_preview_coalesces_tokens_without_losing_final_text(monkeypatch):
    raw = json.dumps({'text': 'A detailed explanation. ' * 100})
    lines = [json.dumps({'message': {'content': char}}) for char in raw]
    lines.append(json.dumps({'done': True, 'message': {'content': ''}}))
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text='\n'.join(lines)))
    client = httpx.Client
    monkeypatch.setattr('notetaker.note_provider.httpx.Client', lambda **kwargs: client(transport=transport, **kwargs))
    monkeypatch.setattr('notetaker.note_provider.monotonic', lambda: 1.0)
    previews = []
    result = OllamaNotes(Settings()).stream_chat({}, previews.append)
    assert result['message']['content'] == raw
    assert len(previews) == 2
    assert previews[-1] == 'A detailed explanation. ' * 100
