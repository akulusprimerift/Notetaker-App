from datetime import timedelta

from sqlalchemy import event, select

from notetaker.diagnostics import processing_snapshot
from notetaker.models import Course, Job, Lecture, Owner, now
from test_workspace import setup, login, course, lecture  # noqa: F401


def test_diagnostics_auth_scope_and_privacy(setup):
    app, client, _ = setup
    assert client.get('/diagnostics/processing').status_code == 401
    headers = login(client)
    parent = course(client, headers)
    visible = lecture(client, headers, parent['id'])
    hidden = lecture(client, headers, parent['id'])
    stamp = now()
    with app.state.sessions() as db:
        owner = db.scalar(select(Owner.id))
        db.get(Lecture, hidden['id']).tombstoned = True
        for key, lecture_id, epoch, audio_epoch in [
            ('visible', visible['id'], 1, None), ('deleted', hidden['id'], 1, None),
            ('old-lifecycle', visible['id'], 0, None), ('old-audio', visible['id'], 1, 0),
        ]:
            db.add(Job(lecture_id=lecture_id, logical_key=key, kind='notes.generate',
                status='due', lifecycle_epoch=epoch, audio_epoch=audio_epoch,
                input_revision='PRIVATE SOURCE', error_code='PRIVATE ERROR', due_at=stamp))
        db.commit()
        assert processing_snapshot(db, 'another-owner')['groups'] == []
        assert len(processing_snapshot(db, owner)['groups']) == 1
    response = client.get('/diagnostics/processing')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.json()['groups'][0]['count'] == 1
    assert 'PRIVATE' not in response.text and visible['id'] not in response.text
    with app.state.sessions() as db:
        db.get(Course, parent['id']).tombstoned = True
        db.commit()
    assert client.get('/diagnostics/processing').json()['groups'] == []


def test_queue_timing_retry_and_expired_lease_are_read_only(setup):
    app, client, _ = setup
    headers = login(client)
    item = lecture(client, headers, course(client, headers)['id'])
    stamp = now()
    with app.state.sessions() as db:
        owner = db.scalar(select(Owner.id))
        for index, (status, seconds, lease) in enumerate([
            ('due', -30, None), ('due', 20, None), ('due', 0, None),
            ('running', -100, stamp), ('running', -100, None),
            ('running', -100, stamp + timedelta(seconds=60)),
            ('failed', -100, None), ('completed', -100, None), ('cancelled', -100, None),
        ]):
            db.add(Job(lecture_id=item['id'], logical_key=str(index), kind='speech.window',
                status=status, lifecycle_epoch=1, audio_epoch=1, input_revision='synthetic',
                due_at=stamp + timedelta(seconds=seconds), lease_expires_at=lease, attempts=2))
        db.commit()
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        connection = db.connection()
        event.listen(connection, 'before_cursor_execute', record)
        try:
            result = processing_snapshot(db, owner, sampled_at=stamp)
        finally:
            event.remove(connection, 'before_cursor_execute', record)
        assert len(statements) == 1 and statements[0].startswith('SELECT')
        groups = {row['status']: row for row in result['groups']}
        assert groups.keys() == {'due', 'running', 'failed'}
        assert groups['due']['ready_count'] == 2
        assert groups['due']['delayed_count'] == 1
        assert groups['due']['oldest_due_seconds'] == 30
        assert groups['running']['expired_lease_count'] == 2
        assert groups['running']['oldest_due_seconds'] is None
        assert all(job.attempts == 2 for job in db.scalars(select(Job)))
