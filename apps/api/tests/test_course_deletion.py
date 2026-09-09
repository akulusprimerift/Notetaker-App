from uuid import uuid4
from sqlalchemy import select
from test_workspace import setup, login, course, lecture
from notetaker import models as m
from notetaker.course_deletion import reconcile_courses


def test_course_delete_requires_current_children_and_fences_access(setup):
    app, client, _ = setup
    headers = login(client)
    parent = course(client, headers)
    child = lecture(client, headers, parent['id'])
    path = '/courses/' + parent['id']
    headers = {**headers, 'idempotency-key': str(uuid4())}
    assert client.post(path+'/deletion', headers=headers, json={'expected_lecture_ids': []}).status_code == 409
    body = {'expected_lecture_ids': [child['id']]}
    response = client.post(path+'/deletion', headers=headers, json=body)
    assert response.status_code == 202, response.text
    assert client.get('/courses').json() == []
    assert client.get(path+'/lectures').status_code == 404
    assert client.get('/lectures/'+child['id']+'/transcript').status_code == 404
    assert client.post(path+'/lectures', headers={**headers, 'idempotency-key': str(uuid4())}, json={'title':'Late'}).status_code == 404
    assert client.post(path+'/deletion', headers=headers, json=body).status_code == 202
    with app.state.sessions() as db:
        assert len(list(db.scalars(select(m.Deletion)))) == 1
        assert db.get(m.Lecture, child['id']).tombstoned


def test_empty_course_deletion_is_complete_and_retains_tombstone(setup):
    app, client, _ = setup
    headers = login(client)
    parent = course(client, headers)
    response = client.post('/courses/'+parent['id']+'/deletion', headers=headers, json={'expected_lecture_ids': []})
    assert response.status_code == 202, response.text
    assert response.json()['status'] == 'complete'
    reconcile_courses(app.state.sessions)
    with app.state.sessions() as db:
        row = db.get(m.Course, parent['id'])
        assert row.tombstoned and row.name == 'Deleted course'
