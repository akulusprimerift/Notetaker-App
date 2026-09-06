from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
import os
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, func, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from starlette.websockets import WebSocketDisconnect

from notetaker.config import Settings
from notetaker.main import create_app
from notetaker.models import Bootstrap, Session, Course, Lecture, CommandReceipt, SettingsVersion, LectureUpdate, Outbox, Owner, now
from notetaker.security import digest

ORIGIN="http://127.0.0.1:3000"
TOKEN="test-only-bootstrap-token-"+"x"*40
ROOT=Path(__file__).resolve().parents[3]


def migrate(app):
    config=Config(str(ROOT/"alembic.ini"))
    with app.state.engine.begin() as connection:
        config.attributes["connection"]=connection
        command.upgrade(config,"head")


@pytest.fixture
def setup(tmp_path):
    postgres=os.environ.get('NOTETAKER_TEST_DATABASE_URL')
    admin=None
    schema='verify_'+uuid4().hex
    if postgres:
        if not postgres.startswith('postgresql+psycopg://'):
            raise ValueError('Integration tests require a PostgreSQL URL')
        admin=create_engine(postgres)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url=make_url(postgres).update_query_dict({'options':f'-csearch_path={schema}'}).render_as_string(hide_password=False)
        settings=Settings(database_url=url,preview=False,allowed_hosts=['testserver'])
    else:
        settings=Settings(database_url=f"sqlite:///{(tmp_path/'workspace.db').as_posix()}",preview=True,allowed_hosts=['testserver'])
    app=create_app(settings)
    migrate(app)
    with app.state.sessions() as db:
        db.add(Bootstrap(id=1,token_hash=digest(TOKEN),expires_at=now()+timedelta(minutes=10)))
        db.commit()
    try:
        with TestClient(app) as client:
            yield app,client,settings
    finally:
        app.state.engine.dispose()
        if admin:
            # Only this test's fresh random schema is removed, never the user's database.
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def login(client):
    response=client.post('/session/bootstrap',json={"token":TOKEN},headers={"origin":ORIGIN})
    assert response.status_code==200,response.text
    return {"origin":ORIGIN,"x-csrf-token":response.json()["csrf_token"],"idempotency-key":str(uuid4())}


def course(client,headers):
    response=client.post('/courses',json={"name":"Algorithms","code":"CS 201"},headers={**headers,"idempotency-key":str(uuid4())})
    assert response.status_code==201,response.text
    return response.json()


def lecture(client,headers,course_id):
    response=client.post(f'/courses/{course_id}/lectures',json={"title":"Binary search"},headers={**headers,"idempotency-key":str(uuid4())})
    assert response.status_code==201,response.text
    return response.json()


def test_migration_creates_foundation_and_is_repeatable(setup):
    app,client,_=setup
    migrate(app)
    tables=set(inspect(app.state.engine).get_table_names())
    assert {'owners','sessions','courses','lectures','settings_versions','jobs','outbox_events','inbox_events','command_receipts','lecture_updates'}<=tables
    assert client.get('/health').json()=={"status":"ok"}


def test_sqlite_is_explicit_preview_only():
    with pytest.raises(ValueError,match='explicit'):
        Settings(database_url='sqlite:///unapproved.db',preview=False)


def test_bootstrap_is_once_cookie_private_and_session_reloads(setup):
    app,client,_=setup
    headers=login(client)
    cookie=client.cookies.get('nt_session')
    assert cookie and TOKEN not in cookie
    assert client.get('/session').json()['csrf_token']==headers['x-csrf-token']
    assert client.post('/session/bootstrap',json={"token":TOKEN},headers={"origin":ORIGIN}).status_code==401
    with app.state.sessions() as db:
        assert db.scalar(select(Session)).token_hash==digest(cookie)
        assert db.scalar(select(Bootstrap)).used


def test_bootstrap_rejects_cross_origin_without_consuming_secret(setup):
    _,client,_=setup
    assert client.post('/session/bootstrap',json={"token":TOKEN},headers={"origin":"https://attacker.invalid"}).status_code==403
    login(client)


@pytest.mark.parametrize('path',['/courses','/courses/unknown/lectures','/lectures/unknown/snapshot','/lectures/unknown/sources/v1','/lectures/unknown/audio/a1','/jobs/unknown'])
def test_private_routes_require_session(setup,path):
    _,client,_=setup
    assert client.get(path).status_code==401


def test_csrf_and_origin_required_for_writes(setup):
    _,client,_=setup
    headers=login(client)
    for override in [{"origin":"https://attacker.invalid"},{"x-csrf-token":"wrong"},{"origin":""}]:
        assert client.post('/courses',json={"name":"private"},headers={**headers,**override}).status_code==403
    assert client.get('/courses').json()==[]


def test_create_reopen_and_restart_persist_course_lecture_settings(setup):
    app,client,settings=setup
    headers=login(client)
    created=course(client,headers)
    saved=lecture(client,headers,created['id'])
    result=client.get(f"/lectures/{saved['id']}/snapshot").json()
    assert result['lecture']['title']=='Binary search'
    assert result['settings']=={'depth':'detailed','format':'topic_outline','ai_explanations':False,'version':1}
    assert result['capture']=={'status':'not_started','available':False}
    assert result['notes']['blocks']==[]
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Outbox))==1
        assert db.scalar(select(func.count()).select_from(LectureUpdate))==1
    cookie=client.cookies.get('nt_session')
    app.state.engine.dispose()
    restarted=create_app(settings)
    with TestClient(restarted) as reopened:
        reopened.cookies.set('nt_session',cookie)
        assert reopened.get('/courses').json()[0]['id']==created['id']
        assert reopened.get(f"/lectures/{saved['id']}/snapshot").json()['update_cursor']==1


def test_identical_request_replays_and_changed_body_conflicts(setup):
    _,client,_=setup
    headers=login(client)
    one=client.post('/courses',json={"name":"Algorithms"},headers=headers)
    two=client.post('/courses',json={"name":"Algorithms"},headers=headers)
    assert one.status_code==two.status_code==201
    assert one.json()==two.json()
    assert len(client.get('/courses').json())==1
    assert client.post('/courses',json={"name":"Different"},headers=headers).status_code==409


def test_concurrent_retries_create_one_course(setup):
    app,client,_=setup
    headers=login(client)
    cookie=client.cookies.get('nt_session')
    def send(_):
        # Independent client instances share only the database/session cookie.
        other=TestClient(app)
        other.cookies.set('nt_session',cookie)
        return other.post('/courses',json={'name':'Concurrent'},headers=headers)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(send,range(2)))
    assert [r.status_code for r in responses]==[201,201],[r.text for r in responses]
    assert responses[0].json()['id']==responses[1].json()['id']
    assert len(client.get('/courses').json())==1


def test_cross_owner_course_and_source_access_is_denied(setup):
    app,client,_=setup
    headers=login(client)
    created=course(client,headers)
    saved=lecture(client,headers,created['id'])
    # A forged session's owner ID is not a trusted route filter or source authority.
    with app.state.sessions() as db:
        session=db.scalar(select(Session))
        original=session.owner_id
    from notetaker.main import owned_course,owned_lecture
    from fastapi import HTTPException
    with app.state.sessions() as db:
        for action,id in [(owned_course,created['id']),(owned_lecture,saved['id'])]:
            with pytest.raises(HTTPException) as caught:
                action(db,'unrelated-owner',id)
            assert caught.value.status_code==404
    assert client.get('/courses/unknown/lectures').status_code==404
    assert client.get(f"/lectures/{saved['id']}/sources/unknown").status_code==404


def test_tombstone_hides_lecture_and_blocks_idempotent_replay(setup):
    app,client,_=setup
    headers=login(client)
    created=course(client,headers)
    headers['idempotency-key']=str(uuid4())
    path=f"/courses/{created['id']}/lectures"
    saved=client.post(path,json={'title':'Removed'},headers=headers).json()
    with app.state.sessions() as db:
        db.get(Lecture,saved['id']).tombstoned=True
        db.commit()
    assert client.get(path).json()==[]
    for suffix in ['snapshot','sources/v1','audio/a1']:
        assert client.get(f"/lectures/{saved['id']}/{suffix}").status_code==404
    assert client.post(path,json={'title':'Removed'},headers=headers).status_code==404


def test_validation_does_not_echo_secrets_or_private_input(setup):
    _,client,_=setup
    headers=login(client)
    sentinel='PRIVATE-LECTURE-CONTENT'
    response=client.post('/courses',json={'name':sentinel,'owner_id':sentinel},headers=headers)
    assert response.status_code==422
    assert sentinel not in response.text
    assert response.headers['cache-control']=='no-store'
    assert len(response.headers['x-trace-id'])==36
    assert client.post('/courses',json={'name':'   '},headers=headers).status_code==422


def test_session_expiry_and_logout_revoke_access(setup):
    app,client,_=setup
    headers=login(client)
    cookie=client.cookies.get('nt_session')
    assert client.post('/session/logout',headers=headers).status_code==204
    assert client.get('/courses').status_code==401
    with app.state.sessions() as db:
        row=db.scalar(select(Session))
        assert row.revoked
        row.revoked=False
        row.expires_at=now()-timedelta(seconds=1)
        db.commit()
    # Authentication checks expiry independently of the browser's cookie lifetime.
    client.cookies.set('nt_session',cookie)
    assert client.get('/courses').status_code==401


def test_websocket_requires_session_origin_and_lecture_authority(setup):
    app,client,_=setup
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/lectures/unknown/updates',headers={'origin':ORIGIN}):pass
    headers=login(client)
    saved=lecture(client,headers,course(client,headers)['id'])
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/lectures/{saved['id']}/updates",headers={'origin':'https://attacker.invalid'}):pass
    with client.websocket_connect(f"/lectures/{saved['id']}/updates",headers={'origin':ORIGIN}) as socket:
        assert socket.receive_json()=={'kind':'snapshot_required','lecture_id':saved['id']}


def test_database_rejects_orphan_lecture(setup):
    app,_,_=setup
    with app.state.sessions() as db:
        db.add(Lecture(course_id='absent',title='Orphan'))
        with pytest.raises(IntegrityError):db.commit()


def test_bootstrap_expiry_and_unknown_host(setup):
    app,client,_=setup
    with app.state.sessions() as db:
        db.get(Bootstrap,1).expires_at=now()-timedelta(seconds=1)
        db.commit()
    assert client.post('/session/bootstrap',json={'token':TOKEN},headers={'origin':ORIGIN}).status_code==401
    assert client.get('/health',headers={'host':'attacker.invalid'}).status_code==400


def test_migration_keeps_existing_data_and_refuses_destructive_downgrade(setup):
    app,client,_=setup
    headers=login(client)
    saved=course(client,headers)
    migrate(app)
    assert client.get('/courses').json()[0]['id']==saved['id']
    config=Config(str(ROOT/'alembic.ini'))
    with app.state.engine.begin() as connection:
        config.attributes['connection']=connection
        with pytest.raises(RuntimeError,match='Destructive downgrade'):
            command.downgrade(config,'base')
    assert client.get('/courses').json()[0]['id']==saved['id']


def test_session_cookie_flags_and_failed_input_do_not_consume_unlock(setup):
    _,client,_=setup
    assert client.post('/session/bootstrap',json={'token':'private'},headers={'origin':ORIGIN}).status_code==422
    response=client.post('/session/bootstrap',json={'token':TOKEN},headers={'origin':ORIGIN})
    assert response.status_code==200
    cookie=response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'path=/' in cookie


def test_non_loopback_requires_https_and_secure_cookie():
    with pytest.raises(ValueError,match='HTTPS'):
        Settings(web_origin='http://example.com')
    with pytest.raises(ValueError,match='secure session'):
        Settings(web_origin='https://example.com',secure_cookies=False)
