from types import SimpleNamespace
from uuid import uuid4
from sqlalchemy import select, func
from test_workspace import setup, login, course
from test_capture import capture, upload, chunk
from notetaker import models as m
from notetaker.transcription import lock_lecture, schedule
from notetaker.speech_provider import WhisperProvider


def save(client, headers, ident, version, terms, key=None):
    return client.post('/courses/' + ident + '/terminology',
        headers={**headers, 'idempotency-key': key or str(uuid4())},
        json={'expected_version': version, 'terms': terms})


def test_terms_are_versioned_validated_and_idempotent(setup):
    app, client, _ = setup
    headers = login(client); ident = course(client, headers)['id']
    endpoint = '/courses/' + ident + '/terminology'
    assert client.get(endpoint).json()['version'] == 0
    assert client.post(endpoint, json={'expected_version': 0, 'terms': []}).status_code == 403
    key = str(uuid4())
    first = save(client, headers, ident, 0, ['mitochondria', 'ATP'], key)
    assert first.status_code == 200, first.text
    assert save(client, headers, ident, 0, ['mitochondria', 'ATP'], key).json() == first.json()
    assert save(client, headers, ident, 0, ['different']).status_code == 409
    for terms in [['ATP', 'atp'], ['x' * 61], ['bad\nterm'], [str(i) + 'x' * 48 for i in range(30)]]:
        assert save(client, headers, ident, 1, terms).status_code == 422
    assert save(client, headers, ident, 1, []).json()['version'] == 2
    assert save(client, headers, str(uuid4()), 0, ['ATP']).status_code == 404
    with app.state.sessions() as db:
        assert db.scalar(select(m.CourseTerminology).where(m.CourseTerminology.version == 1)).terms == ['mitochondria', 'ATP']
    response = client.post('/courses/' + ident + '/deletion', headers={**headers, 'idempotency-key': str(uuid4())}, json={'expected_lecture_ids': []})
    assert response.status_code == 202
    assert client.get(endpoint).status_code == 404
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(m.CourseTerminology)) == 0


def test_future_windows_pin_terms_without_changing_existing_windows(capture):
    app, client, headers, path, run = capture
    with app.state.sessions() as db:
        ident = db.get(m.Lecture, path.split('/')[-1]).course_id
    first = save(client, headers, ident, 0, ['Dijkstra']).json()
    assert upload(client, headers, path, run, count=480000).status_code == 200
    with app.state.sessions() as db:
        lecture = lock_lecture(db, path.split('/')[-1]); schedule(db, lecture); db.commit()
        old = {w.id: w.terminology for w in db.scalars(select(m.SpeechWindow))}
    assert old and all(value == first for value in old.values())
    second = save(client, headers, ident, 1, ['Bellman-Ford']).json()
    assert upload(client, headers, path, run, sequence=1, count=480000).status_code == 200
    with app.state.sessions() as db:
        lecture = lock_lecture(db, path.split('/')[-1]); schedule(db, lecture); db.commit()
        windows = list(db.scalars(select(m.SpeechWindow)))
        assert any(w.id not in old for w in windows)
        assert all(w.terminology == (old[w.id] if w.id in old else second) for w in windows)
        assert db.scalar(select(func.count()).select_from(m.TranscriptVersion)) == 0


def test_whisper_receives_pinned_hints_as_prompt_not_transcript(monkeypatch):
    captured = {}
    provider = WhisperProvider(SimpleNamespace())
    def transcribe(audio, **kwargs):
        captured.update(kwargs)
        return iter([]), None
    provider.model = SimpleNamespace(transcribe=transcribe)
    provider.metadata = {'provider': 'synthetic-adapter-check'}
    monkeypatch.setattr(provider, 'load', lambda: None)
    window = SimpleNamespace(core_start=0, core_end=960, context_start=0, context_end=960,
        terminology={'version_id': 'test', 'version': 1, 'terms': ['Dijkstra', 'Bellman-Ford']})
    audio, _ = chunk({'id': 'test', 'capture_epoch': 1}, amplitude=0)
    result = provider.transcribe(audio, window, 48000)
    assert captured['initial_prompt'] == 'Dijkstra, Bellman-Ford'
    assert result['segments'] == [] and result['outcome'] == 'silence'
    assert result['metadata']['terminology'] == window.terminology
