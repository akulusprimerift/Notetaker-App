from uuid import uuid4
from copy import deepcopy
from sqlalchemy import select, func
from test_workspace import setup, course, lecture
from test_capture import capture
from test_transcription import speech
from test_notes import notes, correction
from test_note_edits import generated, command
from test_lifecycle import remove
from notetaker import models as m
from notetaker.lifecycle import reconcile_deletion


def assess(client, headers, path, deck, version=0, rating='again', key=None):
    return client.post(path + '/study/learning/reviews',
        headers={**headers, 'idempotency-key': key or str(uuid4())},
        json={'revision_id': deck['revision_id'], 'block_id': deck['cards'][0]['id'],
            'expected_version': version, 'rating': rating})


def test_learning_preserves_answers_and_idempotent_append_only_ratings(notes):
    app, client, headers, path, _ = notes
    assert client.get(path + '/study/learning').json()['cards'] == []
    saved = generated(app, client, path)
    deck = client.get(path + '/study/learning').json()
    assert deck['revision_id'] == saved['id'] and deck['cards']
    card = deck['cards'][0]
    assert [p['text'] for p in card['passages']] == [p['text'] for p in saved['content']['blocks'][0]['passages']]
    assert card['sources'] and card['review']['version'] == 0
    assert assess(client, {}, path, deck).status_code == 403
    key = str(uuid4())
    first = assess(client, headers, path, deck, key=key)
    assert first.status_code == 200, first.text
    assert assess(client, headers, path, deck, key=key).json() == first.json()
    assert assess(client, headers, path, deck, key=key, rating='confident').status_code == 409
    assert assess(client, headers, path, deck).status_code == 409
    assert assess(client, headers, path, deck, version=1, rating='confident').json()['version'] == 2
    assert assess(client, headers, path, deck, version=2, rating='unreviewed').json()['version'] == 3
    assert assess(client, headers, path, deck, version=3, rating='mastered').status_code == 422
    assert client.get(path + '/study/learning').json()['cards'][0]['review']['rating'] == 'unreviewed'
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(m.LearningReview)) == 3
        assert db.scalar(select(func.count()).select_from(m.NoteRevision)) == 1


def test_learning_fences_source_corrections_and_selected_edits(notes):
    app, client, headers, path, _ = notes
    saved = generated(app, client, path)
    deck = client.get(path + '/study/learning').json()
    assert assess(client, headers, path, deck, rating='confident').status_code == 200
    passage = saved['content']['blocks'][0]['passages'][0]
    response = command(client, headers, path, {'action': 'save', 'expected_version': 0,
        'base_id': saved['id'], 'passages': [{'id': passage['id'], 'text': 'My revised explanation; preserve the qualification.'}]})
    assert response.status_code == 200, response.text
    updated = client.get(path + '/study/learning').json()
    assert updated['cards'][0]['passages'][0]['student_edited']
    assert updated['cards'][0]['passages'][0]['text'].startswith('My revised')
    assert updated['cards'][0]['review']['version'] == 0
    assert assess(client, headers, path, deck, version=1).status_code == 409
    correction(client, headers, path)
    changed = client.get(path + '/study/learning').json()
    assert changed['omitted'] > 0 and not changed['cards']
    assert assess(client, headers, path, updated).status_code == 409


def test_learning_ownership_and_deletion(notes):
    app, client, headers, path, _ = notes
    generated(app, client, path)
    deck = client.get(path + '/study/learning').json()
    another = lecture(client, headers, course(client, headers)['id'])
    assert assess(client, headers, '/lectures/' + another['id'], deck).status_code == 409
    assert client.get('/lectures/missing/study/learning').status_code == 404
    key = str(uuid4())
    assert assess(client, headers, path, deck, key=key).status_code == 200
    deletion = remove(client, headers, path).json()
    reconcile_deletion(app.state.sessions, app.state.audio_store, deletion['id'])
    assert client.get(path + '/study/learning').status_code == 404
    assert assess(client, headers, path, deck, key=key).status_code == 404
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(m.LearningReview)) == 0
    client.cookies.clear()
    assert client.get('/lectures/' + another['id'] + '/study/learning').status_code == 401


def test_learning_does_not_drop_unsupported_qualifiers_from_blocks(notes):
    app, client, _, path, _ = notes
    saved = generated(app, client, path)
    # Synthetic mixed-evidence fixture: do not turn an incomplete section into an answer.
    with app.state.sessions() as db:
        row = db.get(m.NoteRevision, saved['id'])
        content = deepcopy(row.content)
        content['blocks'][0]['passages'].append({'id': 'extra', 'text': 'An unsupported qualification.',
            'evidence_kind': 'ai_explanation', 'sources': []})
        row.content = content
        db.commit()
    result = client.get(path + '/study/learning').json()
    assert result['cards'] == [] and result['omitted'] == 1


def test_learning_migration_preserves_existing_library(tmp_path):
    from alembic import command as migration
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import Session
    from test_workspace import ROOT
    engine = create_engine('sqlite:///' + (tmp_path / 'upgrade.db').as_posix())
    config = Config(str(ROOT / 'alembic.ini'))
    try:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            migration.upgrade(config, '0015')
        with Session(engine) as db:
            owner = m.Owner(); db.add(owner); db.flush()
            course_row = m.Course(owner_id=owner.id, name='Retained course'); db.add(course_row); db.flush()
            row = m.Lecture(course_id=course_row.id, title='Retained lecture'); db.add(row); db.commit()
            lecture_id = row.id
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            migration.upgrade(config, 'head')
        with Session(engine) as db:
            assert db.get(m.Lecture, lecture_id).title == 'Retained lecture'
            assert db.scalar(select(func.count()).select_from(m.LearningReview)) == 0
        assert 'learning_reviews' in inspect(engine).get_table_names()
    finally:
        engine.dispose()
