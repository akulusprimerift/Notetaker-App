import json

import httpx
import pytest

from notetaker.note_provider import NoteFailure
from notetaker.provider_bridge import ProviderBridge


def test_desktop_bridge_preview_arrives_before_final_result(monkeypatch):
    previews = []

    class Body(httpx.SyncByteStream):
        def __iter__(self):
            yield (json.dumps({'type': 'preview', 'raw': '{"text":"Growing'}) + '\n').encode()
            assert previews == ['Growing']
            yield (json.dumps({'type': 'result', 'raw': '{"text":"Growing notes"}', 'metrics': {'tokens': 2}}) + '\n').encode()

    def handler(request):
        assert request.headers['X-Notetaker-Bridge-Token'] == 'synthetic-token'
        assert json.loads(request.content)['stream'] is True
        return httpx.Response(200, stream=Body())

    client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: client(**kwargs, transport=httpx.MockTransport(handler)))
    result = ProviderBridge('http://bridge', 'synthetic-token').generate('openai/test', 'digest', [], previews.append)
    assert result == ('{"text":"Growing notes"}', {'tokens': 2})


@pytest.mark.parametrize('body,code', [
    ('', 'provider_unavailable'),
    ('invalid\n', 'provider_unavailable'),
    ('{"type":"error","code":"provider_authentication"}\n', 'provider_authentication'),
])
def test_desktop_bridge_does_not_publish_interrupted_or_failed_stream(monkeypatch, body, code):
    client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: client(**kwargs,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body))))
    with pytest.raises(NoteFailure) as failure:
        ProviderBridge('http://bridge', 'token').generate('openai/test', 'digest', [], lambda text: None)
    assert failure.value.code == code
