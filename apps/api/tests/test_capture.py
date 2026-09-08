import hashlib
import io
import json
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from notetaker.models import (CaptureRun, UploadReservation, AudioChunk, Job, Outbox,
    LectureUpdate, AudioManifestRevision, Lecture, now)
from test_workspace import setup, login, course, lecture, migrate


class MemoryStore:
    available = True
    def __init__(self):
        self.objects = {}
        self.fail = False
        self.after_write = None
    def ready(self):
        if self.fail: raise RuntimeError('synthetic unavailable')
    def write_verified(self, key, data, checksum):
        self.objects[key] = data
        if self.after_write: self.after_write()
        if self.fail: raise RuntimeError('synthetic failed readback')
        assert hashlib.sha256(self.read(key)).hexdigest() == checksum
    def read(self, key): return self.objects[key]
    def list_keys(self, prefix):
        self.ready()
        return [key for key in self.objects if key.startswith(prefix)]
    def delete_verified(self, key):
        self.ready()
        self.objects.pop(key,None)


@pytest.fixture
def capture(setup):
    app, client, settings = setup
    app.state.audio_store = MemoryStore()
    headers = login(client)
    saved = lecture(client, headers, course(client, headers)['id'])
    path = f"/lectures/{saved['id']}"
    token = 'synthetic-capture-grant-' + uuid4().hex
    body = {'sample_rate':48000, 'grant':token, 'expected_capture_epoch':0}
    response = client.post(path+'/capture-runs', json=body, headers=headers)
    assert response.status_code == 201, response.text
    run = response.json()
    return app, client, {**headers,'x-capture-grant':token}, path, run


def chunk(run, sequence=0, start=None, count=960, amplitude=1):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
        wav.writeframes(int(amplitude).to_bytes(2, 'little', signed=True)*count)
    data = buffer.getvalue()
    identity = {'run_id':run['id'], 'capture_epoch':run['capture_epoch'], 'sequence':sequence,
        'start_sample':sequence*count if start is None else start, 'sample_count':count,
        'sample_rate':48000, 'channels':1, 'encoding':'pcm_s16le_wav',
        'sha256':hashlib.sha256(data).hexdigest(), 'byte_length':len(data)}
    return data, identity


def upload(client, headers, path, run, sequence=0, **kwargs):
    data, identity = chunk(run, sequence, **kwargs)
    return client.put(f"{path}/capture-runs/{run['id']}/chunks/{sequence}", content=data,
        headers={**headers, 'x-chunk-identity':json.dumps(identity), 'content-type':'audio/wav'})


def manifest(client, path, run):
    return client.get(f"{path}/capture-runs/{run['id']}/manifest").json()


def seal(client, headers, path, run, last=0, samples=960, gaps=None):
    return client.post(f"{path}/capture-runs/{run['id']}/seal", headers=headers, json={
        'expected_version':manifest(client,path,run)['manifest_version'], 'last_sequence':last,
        'final_sample_count':samples, 'gaps':gaps or []})


def test_verified_ack_requires_object_readback_and_atomic_metadata(capture):
    app, client, headers, path, run = capture
    app.state.audio_store.fail = True
    assert upload(client,headers,path,run).status_code == 503
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(UploadReservation)) == 1
        assert db.scalar(select(func.count()).select_from(AudioChunk)) == 0
        assert db.scalar(select(func.count()).select_from(Job)) == 0
    app.state.audio_store.fail = False
    response = upload(client,headers,path,run)
    assert response.status_code == 200, response.text
    assert response.json()['storage_state'] == 'verified'
    with app.state.sessions() as db:
        job = db.scalar(select(Job))
        assert job.status == 'due'
        assert db.scalar(select(Outbox).where(Outbox.event_type == 'audio.verified')).entity_id == job.id
        assert db.scalar(select(LectureUpdate).where(LectureUpdate.kind == 'audio.verified')).entity_id == job.id
    assert client.get(f"{path}/audio-chunks/{response.json()['chunk_id']}").content == chunk(run)[0]


def test_lost_ack_retries_are_identical_and_conflicting_audio_is_rejected(capture):
    app, client, headers, path, run = capture
    first = upload(client,headers,path,run)
    second = upload(client,headers,path,run)
    assert first.json() == second.json()
    assert upload(client,headers,path,run,amplitude=2).status_code == 409
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_out_of_order_coverage_never_skips_missing_audio(capture):
    _, client, headers, path, run = capture
    assert upload(client,headers,path,run,1).status_code == 200
    assert manifest(client,path,run)['saved_through_samples'] == 0
    stopped = seal(client,headers,path,run,last=1,samples=1920)
    assert stopped.status_code == 200 and not stopped.json()['complete']
    assert upload(client,headers,path,run).status_code == 200
    saved = manifest(client,path,run)
    assert saved['complete'] and saved['saved_through_samples'] == 1920
    assert upload(client,headers,path,run,2).status_code == 409


@pytest.mark.parametrize('sequence,start', [(0,1),(1,959),(1,961),(2,500)])
def test_overlaps_and_invalid_adjacency_are_rejected(capture, sequence, start):
    _, client, headers, path, run = capture
    if sequence: assert upload(client,headers,path,run).status_code == 200
    assert upload(client,headers,path,run,sequence,start=start).status_code == 409


def test_checksum_and_format_failure_never_reserve_or_ack(capture):
    app, client, headers, path, run = capture
    data, identity = chunk(run)
    for broken in [data[:-1], b'X'+data[1:]]:
        response = client.put(f"{path}/capture-runs/{run['id']}/chunks/0", content=broken, headers={**headers,'x-chunk-identity':json.dumps(identity)})
        assert response.status_code == 422
    bad = bytearray(data); bad[32] = 4
    identity['sha256'] = hashlib.sha256(bad).hexdigest()
    assert client.put(f"{path}/capture-runs/{run['id']}/chunks/0",content=bytes(bad),headers={**headers,'x-chunk-identity':json.dumps(identity)}).status_code == 422
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(UploadReservation)) == 0


def test_start_and_takeover_are_explicit_and_old_owner_is_fenced(capture):
    _, client, headers, path, run = capture
    body = {'sample_rate':48000,'grant':'new-grant-'+uuid4().hex,'expected_capture_epoch':1}
    fresh = {**headers,'idempotency-key':str(uuid4())}
    assert client.post(path+'/capture-runs',json=body,headers=fresh).status_code == 409
    taken = client.post(path+'/capture-takeover',json=body,headers=fresh)
    assert taken.status_code == 201
    assert client.post(path+'/capture-takeover',json=body,headers=fresh).json()['id'] == taken.json()['id']
    assert upload(client,headers,path,run).status_code == 409
    assert client.post(f"{path}/capture-runs/{run['id']}/heartbeat",headers=headers).status_code == 409
    assert manifest(client,path,run)['state'] == 'interrupted'


def test_grant_expiry_renews_only_the_same_owner(capture):
    app, client, headers, path, run = capture
    with app.state.sessions() as db:
        db.get(CaptureRun,run['id']).grant_expires_at = now()-timedelta(seconds=1)
        db.commit()
    assert upload(client,headers,path,run).status_code == 409
    assert client.post(f"{path}/capture-runs/{run['id']}/heartbeat",headers={**headers,'x-capture-grant':'wrong'}).status_code == 409
    assert client.post(f"{path}/capture-runs/{run['id']}/heartbeat",headers=headers).status_code == 200
    assert upload(client,headers,path,run).status_code == 200


def test_upload_finishing_after_tombstone_cannot_commit(capture):
    app, client, headers, path, run = capture
    def remove():
        with app.state.sessions() as db:
            db.get(Lecture,run['lecture_id']).tombstoned = True
            db.commit()
    app.state.audio_store.after_write = remove
    assert upload(client,headers,path,run).status_code == 404
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(AudioChunk)) == 0
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(UploadReservation)).state == 'reserved'


def test_recovery_seals_crash_and_accepts_only_declared_old_audio(capture):
    app, client, headers, path, run = capture
    assert upload(client,headers,path,run).status_code == 200
    token = 'recovery-'+uuid4().hex
    body = {'run_id':run['id'],'grant':token,'expected_capture_epoch':1,'expected_version':1,
        'last_sequence':1,'final_sample_count':1920,'gaps':[]}
    response = client.post(path+'/capture-recovery',json=body,headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()['sealed'] and not response.json()['complete']
    assert response.json()['gaps'][0]['reason'] == 'crash'
    assert upload(client,headers,path,run,1).status_code == 409
    recovery_headers = {**headers,'x-capture-grant':token}
    assert upload(client,recovery_headers,path,run,1).status_code == 200
    assert upload(client,recovery_headers,path,run,2).status_code == 409
    saved = manifest(client,path,run)
    assert saved['complete'] and saved['gaps']
    with app.state.sessions() as db:
        revisions = db.scalars(select(AudioManifestRevision).order_by(AudioManifestRevision.version)).all()
        assert not revisions[0].content['complete'] and revisions[-1].content['complete']


def test_seal_retry_and_stale_or_shrinking_manifest(capture):
    _, client, headers, path, run = capture
    assert upload(client,headers,path,run).status_code == 200
    path_seal = f"{path}/capture-runs/{run['id']}/seal"
    assert client.post(path_seal,json={'expected_version':0,'last_sequence':0,'final_sample_count':960},headers=headers).status_code == 409
    assert seal(client,headers,path,run,samples=959).status_code == 409
    one = seal(client,headers,path,run)
    two = seal(client,headers,path,run)
    assert one.status_code == 200 and one.json() == two.json()


def test_concurrent_chunk_retries_create_one_job(capture):
    app, client, headers, path, run = capture
    cookie = client.cookies.get('nt_session')
    def send(_):
        other = TestClient(app); other.cookies.set('nt_session',cookie)
        return upload(other,headers,path,run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send,range(2)))
    assert [r.status_code for r in responses] == [200,200], [r.text for r in responses]
    assert responses[0].json()['chunk_id'] == responses[1].json()['chunk_id']
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_capture_routes_enforce_session_csrf_and_parent_lecture(capture):
    app, client, headers, path, run = capture
    assert upload(client,{**headers,'x-csrf-token':'wrong'},path,run).status_code == 403
    assert client.get(f"/lectures/unknown/capture-runs/{run['id']}/manifest").status_code == 404
    other = TestClient(app)
    assert other.get(path+'/capture').status_code == 401
    response = upload(client,headers,path,run)
    assert client.get(f"/lectures/unknown/audio-chunks/{response.json()['chunk_id']}").status_code == 404


def test_upload_size_limit_and_seal_precondition(capture):
    _, client, headers, path, run = capture
    _, identity = chunk(run)
    response = client.put(f"{path}/capture-runs/{run['id']}/chunks/0",content=b'x'*(8*1024*1024+1),headers={**headers,'x-chunk-identity':json.dumps(identity)})
    assert response.status_code == 413
    assert client.post(f"{path}/capture-runs/{run['id']}/seal",json={'last_sequence':-1,'final_sample_count':0},headers=headers).status_code == 428


def test_normal_offline_stop_recovery_does_not_invent_a_crash_gap(capture):
    _, client, headers, path, run = capture
    assert upload(client,headers,path,run).status_code == 200
    body = {'run_id':run['id'],'grant':'recovery-'+uuid4().hex,'expected_capture_epoch':1,'expected_version':1,
        'last_sequence':0,'final_sample_count':960,'gaps':[],'interrupted':False}
    first = client.post(path+'/capture-recovery',json=body,headers=headers)
    second = client.post(path+'/capture-recovery',json=body,headers=headers)
    assert first.status_code == 200 and first.json() == second.json()
    assert first.json()['gaps'] == [] and first.json()['complete']


def test_upload_finishing_after_takeover_cannot_acknowledge(capture):
    app, client, headers, path, run = capture
    def takeover():
        with app.state.sessions() as db:
            db.get(Lecture,run['lecture_id']).capture_epoch += 1
            db.get(CaptureRun,run['id']).state = 'interrupted'
            db.commit()
    app.state.audio_store.after_write = takeover
    assert upload(client,headers,path,run).status_code == 409
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(AudioChunk)) == 0


def test_incremental_capture_migration_preserves_existing_workspace(setup):
    # The foundation's repeated-migration test now upgrades through 0002 too.
    # Also compare deployed schema to the complete ORM, catching omitted columns/FKs.
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from notetaker.models import Base
    app, client, _ = setup
    headers = login(client)
    saved = lecture(client,headers,course(client,headers)['id'])
    migrate(app)
    with app.state.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection),Base.metadata) == []
    assert client.get(f"/lectures/{saved['id']}/snapshot").json()['lecture']['title'] == 'Binary search'


def test_lecture_save_status_accounts_for_every_recording_segment(capture):
    _, client, headers, path, first = capture
    assert upload(client,headers,path,first).status_code == 200
    assert seal(client,headers,path,first,last=1,samples=1920).status_code == 200
    token='second-grant-'+uuid4().hex
    response=client.post(path+'/capture-runs',headers={**headers,'idempotency-key':str(uuid4())},
        json={'sample_rate':48000,'grant':token,'expected_capture_epoch':1})
    assert response.status_code == 201
    second=response.json()
    second_headers={**headers,'x-capture-grant':token}
    assert upload(client,second_headers,path,second).status_code == 200
    assert seal(client,second_headers,path,second).json()['complete']
    assert client.get(path+'/snapshot').json()['lecture']['status'] == 'audio_pending'
    recovery_token='recover-'+uuid4().hex
    response=client.post(path+'/capture-recovery',headers=headers,json={'run_id':first['id'],'grant':recovery_token,
        'expected_capture_epoch':2,'expected_version':2,'last_sequence':1,'final_sample_count':1920,'interrupted':False})
    assert response.status_code == 200, response.text
    assert upload(client,{**headers,'x-capture-grant':recovery_token},path,first,1).status_code == 200
    assert client.get(path+'/snapshot').json()['lecture']['status'] == 'audio_saved'
