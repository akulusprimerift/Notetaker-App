from pathlib import Path
import subprocess
import sys
import os
import sysconfig
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from test_workspace import setup, login, course, lecture
from test_capture import capture
from test_transcription import speech
from test_notes import notes
from notetaker.config import Settings
from notetaker.db import database
from notetaker.library_conversion import convert_library
from notetaker.main import create_app
from notetaker.models import Course, NoteRevision
from notetaker.resource_budget import inference_slot


@pytest.mark.parametrize('earlier', [False, True])
def test_service_migration_commits_head_and_retains_earlier_library(tmp_path, earlier):
    import sqlite3
    from contextlib import closing
    from alembic import command
    from alembic.config import Config
    root = Path(__file__).resolve().parents[3]
    file = tmp_path / 'workspace.sqlite3'
    if earlier:
        engine, _ = database('sqlite:///' + file.as_posix())
        config = Config(str(root / 'alembic.ini'))
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, '0012')
            connection.exec_driver_sql("INSERT INTO owners (id,singleton,created_at) VALUES ('owner',1,'2026-10-05')")
            connection.exec_driver_sql("INSERT INTO courses (id,owner_id,name,code,tombstoned,created_at) VALUES ('course','owner','Preserved course','TEST',0,'2026-10-05')")
            connection.exec_driver_sql("INSERT INTO lectures (id,course_id,title,status,lifecycle_epoch,capture_epoch,audio_epoch,update_seq,tombstoned,created_at,audio_removed) VALUES ('lecture','course','Preserved lecture','prepared',1,0,1,1,0,'2026-10-05',0)")
        engine.dispose()
    executable = os.environ.get('NOTETAKER_TEST_SERVICE_EXECUTABLE')
    args = [executable, 'migrate'] if executable else [sys.executable, str(root / 'apps/api/windows_service.py'), 'migrate']
    env = {**os.environ, 'NOTETAKER_DATABASE_URL': 'sqlite:///' + file.as_posix(),
        'NOTETAKER_AUDIO_DIRECTORY': str(tmp_path / 'audio')}
    subprocess.run(args, cwd=root, env=env, check=True, capture_output=True, timeout=180)
    # Reopen in a different connection after the service process exits.
    with closing(sqlite3.connect(file)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('0018',)
        assert connection.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        assert 'keep_audio' in [row[1] for row in connection.execute('PRAGMA table_info(lectures)')]
        if earlier:
            assert connection.execute('SELECT title,keep_audio FROM lectures').fetchone() == ('Preserved lecture', 1)


def test_conversion_preserves_history_audio_exports_and_source(notes, tmp_path):
    app,client,headers,path,_=notes
    from notetaker.note_worker import plan, claim, execute
    from test_notes import FakeNotes
    from test_note_edits import command
    from test_lifecycle import finalize
    from notetaker.lifecycle import reconcile_finalizations
    plan(app.state.sessions)
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
    generated=client.get(path+'/notes').json()['revision']
    edit=command(client,headers,path,{'expected_version':0,'base_id':generated['id'],'action':'save',
        'additional_text':'Preserve my student reasoning:\n    x = 1\nE = mc²'})
    assert edit.status_code==200
    assert finalize(client,headers,path).status_code==202
    plan(app.state.sessions)
    chosen=claim(app.state.sessions)
    if chosen:
        assert execute(app.state.sessions,FakeNotes(),chosen,heartbeat=False)
    reconcile_finalizations(app.state.sessions)
    final=client.get(path+'/finalization').json()['history'][0]
    assert final['status']=='complete'
    final_url=path+'/final-snapshots/'+final['snapshot_id']
    final_export=client.get(final_url+'/export').content
    before=client.get(path+'/notes').json()
    revision=before['revision']
    export=client.get(path+'/notes/revisions/'+revision['id']+'/export').content
    source_objects=dict(app.state.audio_store.objects)
    folder=tmp_path/'converted'
    report=convert_library(app.state.engine,app.state.audio_store,folder)
    assert report['table_counts']['note_revisions']>=1
    assert report['table_counts']['note_edits']>=1 and report['table_counts']['final_snapshots']==1
    assert dict(app.state.audio_store.objects)==source_objects
    assert client.get(path+'/notes').json()==before
    converted=create_app(Settings(_env_file=None,database_url='sqlite:///'+(folder/'workspace.sqlite3').as_posix(),
        audio_directory=str(folder/'audio'),allowed_hosts=['testserver']))
    with TestClient(converted) as other:
        login(other)
        assert other.get(path+'/notes').json()==before
        assert other.get(path+'/notes/revisions/'+revision['id']+'/export').content==export
        assert other.get(path+'/transcript').json()==client.get(path+'/transcript').json()
        assert other.get(final_url+'/export').content==final_export
    for key,data in source_objects.items():
        assert converted.state.audio_store.read(key)==data
    with app.state.sessions() as db:
        assert db.scalar(select(NoteRevision.id).where(NoteRevision.id==revision['id']))==revision['id']
    with pytest.raises(RuntimeError,match='never replaced'):
        convert_library(app.state.engine,app.state.audio_store,folder)


@pytest.mark.parametrize('failure',['missing','corrupt','oversized'])
def test_conversion_missing_audio_is_not_published(capture,tmp_path,failure):
    from test_capture import upload
    app,client,headers,path,run=capture
    assert upload(client,headers,path,run).status_code==200
    if failure=='missing':
        app.state.audio_store.objects.clear()
    elif failure=='corrupt':
        key=next(iter(app.state.audio_store.objects))
        app.state.audio_store.objects[key]=b'corrupt original audio'
    else:
        app.state.audio_store.objects['orphan.wav']=b'x'*(8*1024*1024+1)
    target=tmp_path/'missing-audio'
    with pytest.raises(RuntimeError,match='missing|checksum|limit'):
        convert_library(app.state.engine,app.state.audio_store,target)
    assert not target.exists()
    assert list(tmp_path.glob('missing-audio.pending-*/conversion.pending'))
    assert app.state.engine.url.database and Path(app.state.engine.url.database).exists()


def test_os_inference_lock_excludes_another_process_and_recovers_after_crash(tmp_path):
    filename=tmp_path/'workers.sqlite3'
    engine,sessions=database('sqlite:///'+filename.as_posix())
    code='''import sys
from notetaker.db import database
from notetaker.resource_budget import inference_slot
_,sessions=database(sys.argv[1])
with inference_slot(sessions) as acquired:
    print(acquired,flush=True)
    if acquired: sys.stdin.read()
'''
    # Windows venv python.exe is a redirector; killing it alone leaves its child alive.
    command=[sys._base_executable,'-c',code,str(engine.url)]
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(Path('apps/api').resolve()),sysconfig.get_paths()['purelib']])}
    holder=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,env=env)
    try:
        assert holder.stdout.readline().strip()=='True'
        with inference_slot(sessions) as acquired:
            assert not acquired
        with inference_slot(sessions,'notes.generate') as acquired:
            assert acquired
        challenger=subprocess.run(command,input='',capture_output=True,text=True,timeout=10,env=env)
        assert challenger.returncode==0 and challenger.stdout.strip()=='False'
        holder.kill();holder.wait(timeout=10)
        with inference_slot(sessions) as acquired:
            assert acquired
    finally:
        if holder.poll() is None:
            holder.kill();holder.wait(timeout=10)
        holder.stdin.close();holder.stdout.close();engine.dispose()


def test_sqlite_concurrent_commands_and_reopen_preserve_records(setup):
    app,client,_=setup
    headers=login(client)
    def create(index):
        return client.post('/courses',headers={**headers,'idempotency-key':str(uuid4())},json={'name':'Concurrent '+str(index)})
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(create,range(12)))
    assert all(response.status_code==201 for response in responses)
    filename=app.state.engine.url.database
    engine,sessions=database('sqlite:///'+filename)
    with engine.connect() as connection:
        assert connection.exec_driver_sql('PRAGMA journal_mode').scalar()=='wal'
        assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar()==1
        assert connection.exec_driver_sql('PRAGMA synchronous').scalar()==2
        assert connection.exec_driver_sql('PRAGMA integrity_check').scalar()=='ok'
    with sessions() as db:
        assert len(db.scalars(select(Course)).all())==12
    engine.dispose()
