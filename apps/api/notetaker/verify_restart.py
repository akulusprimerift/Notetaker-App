"""Restart drill using a new SQLite file and uniquely named synthetic services."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import wave
from datetime import timedelta
from uuid import uuid4

import boto3
from botocore.config import Config as S3Config
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL

from .config import Settings
from .main import create_app
from .models import Bootstrap, now
from .security import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    suffix = uuid4().hex
    sqlite_dir = root / '.local' / 'sqlite'
    sqlite_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = sqlite_dir / f'verify-restart-{suffix}.sqlite3'
    database_url = URL.create('sqlite', database=str(sqlite_path)).render_as_string(hide_password=False)
    bucket = 'notetaker-verify-' + suffix
    capture_bucket = 'notetaker-capture-verify-' + suffix
    topic = 'notetaker.verify.' + suffix
    payload = b'Synthetic restart verification; no recorded lecture content.'
    s3 = boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT', 'http://127.0.0.1:8333'),
        aws_access_key_id=os.environ['S3_ACCESS_KEY'], aws_secret_access_key=os.environ['S3_SECRET_KEY'],
        region_name='us-east-1', config=S3Config(signature_version='s3v4', s3={'addressing_style':'path'},
        connect_timeout=3, read_timeout=3, retries={'max_attempts':1}))
    address = os.environ.get('KAFKA_BOOTSTRAP', '127.0.0.1:9092')
    admin = AdminClient({'bootstrap.servers':address})
    bucket_created = topic_created = capture_bucket_created = False
    audio_key = None
    app = consumer = None
    try:
        settings = Settings(database_url=database_url, allowed_hosts=['testserver'], audio_bucket=capture_bucket)
        app = create_app(settings)
        s3.create_bucket(Bucket=capture_bucket)
        capture_bucket_created = True
        with app.state.engine.begin() as connection:
            from alembic import command
            from alembic.config import Config
            config = Config(str(root / 'alembic.ini'))
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
        token = uuid4().hex + uuid4().hex
        with app.state.sessions() as db:
            db.add(Bootstrap(id=1, token_hash=digest(token), expires_at=now()+timedelta(minutes=10)))
            db.commit()
        with TestClient(app) as client:
            response = client.post('/session/open', headers={'origin':settings.web_origin})
            assert response.status_code == 200
            headers = {'origin':settings.web_origin, 'x-csrf-token':response.json()['csrf_token'], 'idempotency-key':suffix}
            response = client.post('/courses', json={'name':'Synthetic restart check', 'code':'VERIFY'}, headers=headers)
            assert response.status_code == 201
            course = response.json()
            response = client.post(f"/courses/{course['id']}/lectures", json={'title':'Persistence check'}, headers=headers)
            assert response.status_code == 201
            lecture = response.json()
            cookie = client.cookies.get('nt_session')
            grant = uuid4().hex + uuid4().hex
            response = client.post(f"/lectures/{lecture['id']}/capture-runs", json={'sample_rate':48000,'grant':grant,'expected_capture_epoch':0}, headers=headers)
            assert response.status_code == 201, response.text
            run = response.json()
            wave_file = io.BytesIO()
            with wave.open(wave_file, 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
                wav.writeframes(b'\x01\x00'*960)
            audio = wave_file.getvalue()
            identity = {'run_id':run['id'],'capture_epoch':run['capture_epoch'],'sequence':0,'start_sample':0,
                'sample_count':960,'sample_rate':48000,'channels':1,'encoding':'pcm_s16le_wav',
                'sha256':hashlib.sha256(audio).hexdigest(),'byte_length':len(audio)}
            audio_key = f"{lecture['id']}/{run['id']}/0/{identity['sha256']}.wav"
            capture_headers = {**headers,'x-capture-grant':grant,'x-chunk-identity':json.dumps(identity)}
            response = client.put(f"/lectures/{lecture['id']}/capture-runs/{run['id']}/chunks/0", content=audio, headers=capture_headers)
            assert response.status_code == 200, response.text
            ack = response.json()
            assert ack['storage_state'] == 'verified'
            response = client.post(f"/lectures/{lecture['id']}/capture-runs/{run['id']}/seal",json={'expected_version':ack['manifest_version'],'last_sequence':0,'final_sample_count':960},headers=capture_headers)
            assert response.status_code == 200 and response.json()['complete']
            lecture = client.get(f"/lectures/{lecture['id']}/snapshot").json()['lecture']

        s3.create_bucket(Bucket=bucket)
        bucket_created = True
        s3.put_object(Bucket=bucket, Key='probe.txt', Body=payload)
        admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)], request_timeout=10)[topic].result(15)
        topic_created = True
        producer = Producer({'bootstrap.servers':address, 'message.timeout.ms':10000, 'acks':'all'})
        failures = []
        producer.produce(topic, key=suffix, value=payload, on_delivery=lambda err,_: failures.append(str(err)) if err else None)
        assert producer.flush(15) == 0 and not failures

        app.state.engine.dispose()
        print('Synthetic SQLite library, audio object and broker record saved. Reopening the library in a fresh API process and restarting object/broker services.', flush=True)
        child_env = os.environ.copy()
        child_env.update(NOTETAKER_DATABASE_URL=database_url, NOTETAKER_AUDIO_BUCKET=capture_bucket,
            NOTETAKER_ALLOWED_HOSTS='["testserver"]', VERIFY_SESSION=cookie, VERIFY_COURSE=course['id'],
            VERIFY_LECTURE=lecture['id'], VERIFY_CHUNK=ack['chunk_id'], VERIFY_AUDIO_SHA256=identity['sha256'])
        probe = """
import hashlib, os
from fastapi.testclient import TestClient
from notetaker.config import Settings
from notetaker.main import create_app
with TestClient(create_app(Settings(allowed_hosts=['testserver']))) as client:
    client.cookies.set('nt_session', os.environ['VERIFY_SESSION'])
    rows = client.get('/courses')
    assert rows.status_code == 200 and rows.json()[0]['id'] == os.environ['VERIFY_COURSE']
    lecture = os.environ['VERIFY_LECTURE']
    assert client.get(f'/lectures/{lecture}/snapshot').json()['lecture']['id'] == lecture
    audio = client.get(f'/lectures/{lecture}/audio-chunks/{os.environ["VERIFY_CHUNK"]}')
    assert audio.status_code == 200 and hashlib.sha256(audio.content).hexdigest() == os.environ['VERIFY_AUDIO_SHA256']
"""
        subprocess.run([sys.executable, '-c', probe], cwd=root, env=child_env, check=True, timeout=60)
        subprocess.run([args.docker, 'compose', '--env-file', '.local/services.env', 'restart', 'seaweed', 'kafka'], cwd=root, check=True, timeout=90)
        deadline = time.monotonic() + 90
        while True:
            try:
                actual = s3.get_object(Bucket=bucket, Key='probe.txt')['Body'].read()
                assert len(actual) == len(payload) and hashlib.sha256(actual).digest() == hashlib.sha256(payload).digest()
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
        consumer = Consumer({'bootstrap.servers':address, 'group.id':topic, 'auto.offset.reset':'earliest', 'enable.auto.commit':False})
        consumer.subscribe([topic])
        deadline = time.monotonic() + 45
        message = None
        while time.monotonic() < deadline:
            candidate = consumer.poll(1)
            if candidate and not candidate.error():
                message = candidate
                break
        assert message is not None and message.value() == payload
        print(json.dumps({'sqlite_library_after_fresh_process':'passed', 'synthetic_audio_after_restart':'passed',
            'object_length_and_sha256_after_restart':'passed', 'broker_record_after_restart':'passed',
            'scope':'synthetic audio through capture API, fresh API process reopening SQLite, and orderly object/broker container restart; not microphone, power-loss or endurance qualification'}, indent=2))
    finally:
        if consumer:
            consumer.close()
        if app:
            app.state.engine.dispose()
        if topic_created:
            admin.delete_topics([topic], request_timeout=10)[topic].result(15)
        if bucket_created:
            s3.delete_object(Bucket=bucket, Key='probe.txt')
            s3.delete_bucket(Bucket=bucket)
        if capture_bucket_created:
            if audio_key:
                s3.delete_object(Bucket=capture_bucket, Key=audio_key)
            s3.delete_bucket(Bucket=capture_bucket)
        for suffix in ('', '-wal', '-shm'):
            try:
                Path(str(sqlite_path) + suffix).unlink()
            except FileNotFoundError:
                pass


if __name__ == '__main__':
    main()
