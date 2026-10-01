"""Transcribed audio is released during live capture unless the student keeps it."""
from uuid import uuid4
from test_workspace import setup, login, course, lecture
from test_capture import capture, upload, seal
from test_transcription import finish_all
from test_lifecycle import finalize
from notetaker import models as m
from notetaker.lifecycle import reconcile_deletion, reconcile_finalizations
from notetaker.speech_worker import plan_pending

RATE = 48000
CHUNK = 2 * RATE


def record(app, client, headers, path, run, chunks=15):
    for sequence in range(chunks):
        assert upload(client, headers, path, run, sequence, count=CHUNK).status_code == 200
    plan_pending(app.state.sessions)
    finish_all(app)


def test_live_passages_release_audio_behind_context(capture):
    app, client, headers, path, run = capture
    assert client.get(path+'/capture').json()['keep_audio'] is False
    record(app, client, headers, path, run)
    # Live cores 0–28 s are final; audio before 26 s (2 s context) is never read again.
    assert len(app.state.audio_store.objects) == 2
    chunks = client.get(path+'/capture').json()['runs'][0]['chunks']
    assert [c['released'] for c in chunks] == [True]*13 + [False]*2
    assert client.get(path+'/audio-chunks/'+chunks[0]['chunk_id']).status_code == 410
    first = client.get(path+'/transcript').json()['snapshot']['segments'][0]
    assert client.get(path+'/sources/'+first['id']+'/audio').status_code == 410
    # Sealing transcribes the retained tail; earlier passages keep their identity.
    assert seal(client, headers, path, run, last=14, samples=15*CHUNK).status_code == 200
    plan_pending(app.state.sessions); finish_all(app)
    final = client.get(path+'/transcript').json()
    assert final['snapshot']['stability'] == 'stable' and final['counts']['failed'] == 0
    assert final['snapshot']['segments'][0]['id'] == first['id']


def test_keeping_audio_retains_every_chunk(capture):
    app, client, headers, path, run = capture
    assert client.put(path+'/audio-retention', headers=headers, json={'keep_audio': True}).status_code == 200
    record(app, client, headers, path, run)
    assert len(app.state.audio_store.objects) == 15
    assert not any(c['released'] for c in client.get(path+'/capture').json()['runs'][0]['chunks'])


def test_retention_requires_csrf_and_rejects_gaps_in_released_audio(capture):
    app, client, headers, path, run = capture
    unsafe = {key: value for key, value in headers.items() if key.lower() != 'x-csrf-token'}
    assert client.put(path+'/audio-retention', headers=unsafe, json={'keep_audio': True}).status_code == 403
    record(app, client, headers, path, run)
    response = seal(client, headers, path, run, last=14, samples=15*CHUNK,
        gaps=[{'reason': 'microphone_lost', 'after_sample': 10*RATE, 'unknown_extent': True}])
    assert response.status_code == 409 and response.json()['error']['code'] == 'gap_released'


def test_finalization_can_delete_all_remaining_audio(capture):
    app, client, headers, path, run = capture
    assert client.put(path+'/audio-retention', headers=headers, json={'keep_audio': True}).status_code == 200
    record(app, client, headers, path, run)
    assert seal(client, headers, path, run, last=14, samples=15*CHUNK).status_code == 200
    state = client.get(path+'/finalization').json()
    response = client.post(path+'/finalization', headers={**headers, 'idempotency-key': str(uuid4())}, json={
        'expected_cursor': state['cursor'], 'expected_edit_version': state['edit_version'],
        'available_only': True, 'discard_audio': True})
    assert response.status_code == 202, response.text
    assert response.json()['snapshot_id']
    state = client.get(path+'/finalization').json()
    assert state['audio_removed'] and state['status'] == 'finalized'
    removal = client.get('/deletions').json()[0]
    assert removal['kind'] == 'audio'
    reconcile_deletion(app.state.sessions, app.state.audio_store, removal['id'])
    assert not app.state.audio_store.objects
    assert client.get(path+'/transcript').json()['snapshot']['segments']


def test_finalization_keeps_audio_by_default(capture):
    app, client, headers, path, run = capture
    assert client.put(path+'/audio-retention', headers=headers, json={'keep_audio': True}).status_code == 200
    record(app, client, headers, path, run, chunks=3)
    assert seal(client, headers, path, run, last=2, samples=3*CHUNK).status_code == 200
    assert finalize(client, headers, path, True).status_code == 202
    reconcile_finalizations(app.state.sessions)
    assert not client.get(path+'/finalization').json()['audio_removed']
    assert len(app.state.audio_store.objects) == 3
    with app.state.sessions() as db:
        assert db.query(m.Deletion).count() == 0


def legacy_lecture(engine):
    """Insert with SQL, since the current ORM model has columns older schemas lack."""
    from sqlalchemy import text
    owner, course_id, lecture_id = str(uuid4()), str(uuid4()), str(uuid4())
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO owners (id, singleton, created_at) VALUES (:id, 1, CURRENT_TIMESTAMP)"), {'id': owner})
        connection.execute(text("INSERT INTO courses (id, owner_id, name, code, created_at) VALUES (:id, :owner, 'Retained course', '', CURRENT_TIMESTAMP)"),
            {'id': course_id, 'owner': owner})
        connection.execute(text("INSERT INTO lectures (id, course_id, title, status, lifecycle_epoch, capture_epoch, audio_epoch, update_seq, tombstoned, created_at) "
            "VALUES (:id, :course, 'Retained lecture', 'audio_saved', 1, 1, 1, 0, 0, CURRENT_TIMESTAMP)"), {'id': lecture_id, 'course': course_id})
    return lecture_id


def test_upgrade_keeps_audio_for_existing_lectures(tmp_path):
    from alembic import command as migration
    from alembic.config import Config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from test_workspace import ROOT
    engine = create_engine('sqlite:///' + (tmp_path / 'upgrade.db').as_posix())
    config = Config(str(ROOT / 'alembic.ini'))
    try:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            migration.upgrade(config, '0017')
        lecture_id = legacy_lecture(engine)
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            migration.upgrade(config, 'head')
        with Session(engine) as db:
            row = db.get(m.Lecture, lecture_id)
            assert row.title == 'Retained lecture' and row.keep_audio is True
            fresh = m.Lecture(course_id=row.course_id, title='New lecture'); db.add(fresh); db.commit()
            assert fresh.keep_audio is False
    finally:
        engine.dispose()
