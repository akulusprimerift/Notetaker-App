from uuid import uuid4
from sqlalchemy import select, func
from test_workspace import setup, course, lecture
from test_capture import capture
from test_transcription import speech
from test_notes import notes, correction
from test_note_edits import generated, command
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
    assert client.get(path + '/study/catch-up?seconds=99999').status_code == 422


def test_catchup_uses_saved_passages_and_current_source_versions(notes):
    app, client, headers, path, run = notes
    saved = generated(app, client, path)
    export = client.get(path + '/notes/revisions/' + saved['id'] + '/export').text
    response = client.get(path + '/study/catch-up?seconds=60')
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['revision_id'] == saved['id'] and data['items']
    source_ids = {source['id'] for source in data['sources']}
    assert all(set(item['source_ids']) <= source_ids for item in data['items'])
    original_passages = {p['text'] for b in saved['content']['blocks'] for p in b['passages']}
    assert all(item['text'] in original_passages for item in data['items'])
    old_id = client.get(path + '/transcript').json()['snapshot']['segments'][0]['id']
    correction(client, headers, path, 'Search requires sorted data; otherwise this method is invalid.')
    updated = client.get(path + '/study/catch-up?seconds=60').json()
    assert all(old_id not in item['source_ids'] for item in updated['items'])
    assert client.get(path + '/notes/revisions/' + saved['id'] + '/export').text == export
    assert client.get(path + '/study/catch-up?run_id=' + run['id'] + '&end_sample=9999999').json()['awaiting_transcript']


def test_catchup_fallback_is_labelled_transcript_and_no_new_inference(notes):
    _, client, _, path, _ = notes
    data = client.get(path + '/study/catch-up').json()
    assert data['revision_id'] is None
    assert all(item['kind'] == 'transcript' for item in data['items'])
    assert 'transcript excerpts' in data['message']


def test_catchup_respects_selected_student_revision(notes):
    app, client, headers, path, _ = notes
    saved = generated(app, client, path)
    passage = saved['content']['blocks'][0]['passages'][0]
    response = command(client, headers, path, {'action': 'save', 'expected_version': 0,
        'base_id': saved['id'], 'passages': [{'id': passage['id'], 'text': 'My careful explanation with its original source.'}]})
    assert response.status_code == 200, response.text
    result = client.get(path + '/study/catch-up?seconds=60').json()
    assert any(item['student_edited'] and item['text'].startswith('My careful') for item in result['items'])


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
