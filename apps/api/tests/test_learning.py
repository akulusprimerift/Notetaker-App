from copy import deepcopy
from sqlalchemy import select, func
from test_workspace import ROOT, setup
from test_capture import capture
from test_transcription import speech
from test_notes import notes, correction
from test_note_edits import generated, command
from notetaker import models as m, question_worker as worker
from notetaker.learning import saved_note_context


def context(app, path):
    with app.state.sessions() as db:
        return saved_note_context(db, db.get(m.Lecture, path.split('/')[-1]))


def test_flashcard_context_uses_current_saved_notes_and_keeps_provenance(notes):
    app, client, headers, path, _ = notes
    saved = generated(app, client, path)
    result = context(app, path)
    assert result['revision_id'] == saved['id'] and result['blocks']
    block = result['blocks'][0]
    assert [passage['text'] for passage in block['passages']] == [
        passage['text'] for passage in saved['content']['blocks'][0]['passages']]
    assert block['passages'][0]['sources'] and block['sources']

    passage = saved['content']['blocks'][0]['passages'][0]
    response = command(client, headers, path, {'action': 'save', 'expected_version': 0,
        'base_id': saved['id'], 'passages': [{'id': passage['id'], 'text': 'My revised explanation; preserve the qualification.'}]})
    assert response.status_code == 200, response.text
    edited = context(app, path)
    assert edited['blocks'][0]['passages'][0]['student_edited']
    assert edited['blocks'][0]['passages'][0]['text'].startswith('My revised')
    assert edited['blocks'][0]['passages'][0]['sources'] == passage['sources']

    correction(client, headers, path)
    changed = context(app, path)
    assert changed['omitted'] > 0 and not changed['blocks']


def test_student_authored_notes_without_transcript_links_can_generate_cards(notes):
    app, client, headers, path, _ = notes
    saved = generated(app, client, path)
    personal_text = 'My personal reminder: compare both endpoints before accepting a local minimum.'
    edited = command(client, headers, path, {'action': 'save', 'expected_version': 0,
        'base_id': saved['id'], 'additional_text': personal_text})
    assert edited.status_code == 200, edited.text

    selected = context(app, path)
    assert selected['revision_id'] == edited.json()['id']
    personal_block = next(block for block in selected['blocks'] if block['topic'] == 'My additions')
    personal_passage = personal_block['passages'][0]
    assert personal_passage['evidence_kind'] == 'student_note'
    assert personal_passage['note_source_id']
    personal_source = next(source for source in personal_block['sources'] if source['id'] == personal_passage['note_source_id'])
    assert personal_source == {'id': personal_passage['note_source_id'], 'text': personal_text,
        'label': 'Student note · My additions', 'source_kind': 'student_note',
        'revision_id': edited.json()['id'], 'passage_id': personal_passage['id']}

    state = client.get(path + '/study/questions').json()
    assert state['has_notes'] and state['revision_id'] == edited.json()['id']
    body = {'revision_id': state['revision_id'], 'preference_id': state['preference_id'],
        'prompt': 'Make one concise card from my personal reminder.', 'cloud_consent': False}
    queued = client.post(path + '/study/questions', json=body,
        headers={**headers, 'idempotency-key': 'student-note-flashcard'})
    assert queued.status_code == 202, queued.text
    with app.state.sessions() as db:
        evidence = db.get(m.QuestionSet, queued.json()['id']).evidence
    assert evidence['revision_id'] == edited.json()['id']
    assert evidence['student_prompt'] == body['prompt']
    note_source = next(source for source in evidence['sources'] if source.get('source_kind') == 'student_note')
    assert note_source['text'] == personal_text
    original_passages = [passage for block in evidence['notes'] for passage in block['passages'] if passage.get('sources')]
    assert original_passages and all(passage['sources'] for passage in original_passages)
    original_source_ids = {citation['source_id'] for passage in original_passages for citation in passage['sources']}
    assert original_source_ids <= {source['id'] for source in evidence['sources']}

    class PersonalNoteCards:
        def generate_questions(self, evidence, preference, preview):
            source = next(source for source in evidence['sources'] if source.get('source_kind') == 'student_note')
            preview('Checking the saved personal note…')
            return [{'kind': 'flashcard', 'objective': 'conditions',
                'question': 'What should be compared before accepting a local minimum?',
                'answer': source['text'], 'citations': [{'source_id': source['id'], 'quote': source['text']}]}], {
                'model': preference.model, 'model_digest': preference.model_digest,
                'semantic_support': 'not_evaluated'}

    claimed = worker.claim(app.state.sessions)
    assert claimed and worker.execute(app.state.sessions, PersonalNoteCards(), claimed, heartbeat=False)
    detail = client.get(path + '/study/questions/' + queued.json()['id']).json()
    assert detail['status'] == 'completed' and not detail['stale']
    assert detail['questions'][0]['citations'][0]['source_id'] == note_source['id']
    assert next(source for source in detail['sources'] if source['id'] == note_source['id'])['label'] == 'Student note · My additions'


def test_unsupported_passage_omits_whole_note_block(notes):
    app, client, _, path, _ = notes
    saved = generated(app, client, path)
    with app.state.sessions() as db:
        row = db.get(m.NoteRevision, saved['id'])
        content = deepcopy(row.content)
        content['blocks'][0]['passages'].append({'id': 'extra', 'text': 'An unsupported qualification.',
            'evidence_kind': 'ai_explanation', 'sources': []})
        row.content = content
        db.commit()
    result = context(app, path)
    assert result['blocks'] == [] and result['omitted'] == 1
    inventory = client.get(path + '/study/questions').json()
    assert not inventory['has_notes'] and inventory['omitted_blocks'] == 1
    assert client.get(path + '/study/learning').status_code == 404
    assert client.get(path + '/study/catch-up').status_code == 404


def test_retired_study_routes_leave_existing_student_records_untouched(notes):
    app, client, _, path, _ = notes
    generated(app, client, path)
    assert client.get(path + '/study/learning').status_code == 404
    assert client.get(path + '/study/catch-up').status_code == 404
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(m.NoteRevision)) == 1
        assert db.scalar(select(func.count()).select_from(m.LearningReview)) == 0


def test_learning_migration_preserves_existing_library(tmp_path):
    from alembic import command as migration
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import Session

    engine = create_engine('sqlite:///' + (tmp_path / 'upgrade.db').as_posix())
    config = Config(str(ROOT / 'alembic.ini'))
    try:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            migration.upgrade(config, '0015')
        from test_audio_retention import legacy_lecture
        lecture_id = legacy_lecture(engine)
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            migration.upgrade(config, 'head')
        with Session(engine) as db:
            assert db.get(m.Lecture, lecture_id).title == 'Retained lecture'
            assert db.scalar(select(func.count()).select_from(m.LearningReview)) == 0
        assert 'learning_reviews' in inspect(engine).get_table_names()
    finally:
        engine.dispose()
