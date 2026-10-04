from uuid import uuid4
from sqlalchemy import select, func
from test_workspace import setup, course, lecture
from test_capture import capture
from test_transcription import speech
from test_notes import notes
from test_note_edits import generated
from test_lifecycle import finalize, remove
from notetaker import models as m
from notetaker.lifecycle import reconcile_deletion


def mark(client, headers, path, run, sample=24000):
    return client.post(path + '/study/marks', headers={**headers, 'idempotency-key': str(uuid4())},
        json={'run_id': run['id'], 'sample': sample})


def test_marks_are_idempotent_and_removal_has_conflict_and_undo(capture):
    app, client, headers, path, run = capture
    body = {'run_id': run['id'], 'sample': 24000}
    fixed = {**headers, 'idempotency-key': str(uuid4())}
    assert client.post(path + '/study/marks', json=body).status_code == 403
    first = client.post(path + '/study/marks', json=body, headers=fixed)
    assert first.status_code == 200, first.text
    row = first.json()
    assert row['awaiting_audio'] and row['recording_number'] == 1
    assert client.post(path + '/study/marks', json=body, headers=fixed).json()['id'] == row['id']
    endpoint = path + '/study/marks/' + row['id']
    def change(version, removed):
        return client.post(endpoint, headers={**headers, 'idempotency-key': str(uuid4())},
            json={'expected_version': version, 'removed': removed})
    assert change(1, True).json()['version'] == 2
    assert change(1, False).status_code == 409
    assert change(2, False).json()['removed'] is False
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(m.ImportantMark)) == 1
        assert db.scalar(select(func.count()).select_from(m.NoteRevision)) == 0


def test_mark_rejects_other_lecture_run_and_outside_retained_audio(capture):
    _, client, headers, path, run = capture
    another = lecture(client, headers, course(client, headers)['id'])
    assert mark(client, headers, '/lectures/' + another['id'], run).status_code == 422
    assert mark(client, headers, path, run, sample=43201 * 48000).status_code == 422
    assert client.get(path + '/study/catch-up?seconds=99999').status_code == 404


def test_final_snapshot_freezes_student_markers_and_deletion_removes_them(notes):
    app, client, headers, path, run = notes
    generated(app, client, path)
    row = mark(client, headers, path, run).json()
    result = finalize(client, headers, path, True)
    assert result.status_code == 202, result.text
    ident = result.json()['snapshot_id']
    frozen = client.get(path + '/final-snapshots/' + ident).json()
    assert frozen['important_marks'][0]['id'] == row['id']
    endpoint = path + '/study/marks/' + row['id']
    assert client.post(endpoint, headers={**headers, 'idempotency-key': str(uuid4())},
        json={'expected_version': 1, 'removed': True}).status_code == 200
    assert client.get(path + '/final-snapshots/' + ident).json() == frozen
    deletion = remove(client, headers, path).json()
    reconcile_deletion(app.state.sessions, app.state.audio_store, deletion['id'])
    assert client.get(path + '/study/marks').status_code == 404
    assert mark(client, headers, path, run).status_code == 404
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(m.ImportantMark)) == 0
