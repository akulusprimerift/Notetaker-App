"""Restart drill using only newly created synthetic resources, never application data."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
import wave
from datetime import timedelta
from uuid import uuid4

import boto3
from botocore.config import Config as S3Config
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from .config import Settings
from .main import create_app
from .models import Bootstrap, now
from .security import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    settings = Settings()
    if settings.preview:
        raise RuntimeError('Restart verification requires PostgreSQL mode')
    root = Path(__file__).resolve().parents[3]
    suffix = uuid4().hex
    schema = 'verify_restart_' + suffix
    bucket = 'notetaker-verify-' + suffix
    capture_bucket = 'notetaker-capture-verify-' + suffix
    topic = 'notetaker.verify.' + suffix
    payload = b'Synthetic restart verification; no recorded lecture content.'
    engine = create_engine(settings.database_url)
    s3 = boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT', 'http://127.0.0.1:8333'),
        aws_access_key_id=os.environ['S3_ACCESS_KEY'], aws_secret_access_key=os.environ['S3_SECRET_KEY'],
        region_name='us-east-1', config=S3Config(signature_version='s3v4', s3={'addressing_style':'path'},
        connect_timeout=3, read_timeout=3, retries={'max_attempts':1}))
    address = os.environ.get('KAFKA_BOOTSTRAP', '127.0.0.1:9092')
    admin = AdminClient({'bootstrap.servers':address})
    schema_created = bucket_created = topic_created = capture_bucket_created = False
    audio_key = None
    app = consumer = None
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_created = True
        url = make_url(settings.database_url).update_query_dict({'options':f'-csearch_path={schema}'}).render_as_string(hide_password=False)
        app = create_app(Settings(database_url=url, preview=False, allowed_hosts=['testserver'], audio_bucket=capture_bucket))
        if not app.state.audio_store.available:
            raise RuntimeError('Recording restart drill requires configured audio storage')
        s3.create_bucket(Bucket=capture_bucket)
        capture_bucket_created = True
        with app.state.engine.begin() as connection:
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
        engine.dispose()
        print('Synthetic course, lecture, object and broker record saved. Restarting the three services.', flush=True)
        subprocess.run([args.docker, 'compose', '--env-file', '.local/services.env', 'restart', 'postgres', 'seaweed', 'kafka'], cwd=root, check=True, timeout=90)
        deadline = time.monotonic() + 90
        while True:
            try:
                with engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                actual = s3.get_object(Bucket=bucket, Key='probe.txt')['Body'].read()
                assert len(actual) == len(payload) and hashlib.sha256(actual).digest() == hashlib.sha256(payload).digest()
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
        with TestClient(app) as client:
            client.cookies.set('nt_session', cookie)
            assert client.get('/courses').json()[0] == course
            snapshot = client.get(f"/lectures/{lecture['id']}/snapshot").json()
            assert snapshot['lecture'] == lecture and snapshot['settings']['depth'] == 'detailed'
            response = client.get(f"/lectures/{lecture['id']}/audio-chunks/{ack['chunk_id']}")
            assert response.status_code == 200 and response.content == audio
            saved = client.get(f"/lectures/{lecture['id']}/capture-runs/{run['id']}/manifest").json()
            assert saved['complete'] and saved['saved_through_samples'] == 960
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
        print(json.dumps({'course_and_lecture_after_restart':'passed', 'object_length_and_sha256_after_restart':'passed',
            'broker_record_after_restart':'passed', 'acknowledged_wav_and_sealed_manifest_after_restart':'passed',
            'scope':'synthetic audio through capture API and orderly container restart; not microphone, power-loss or endurance qualification'}, indent=2))
    finally:
        if consumer:
            consumer.close()
        if app:
            app.state.engine.dispose()
        # These names are generated in this invocation, never accepted from a file or user input.
        if topic_created:
            admin.delete_topics([topic], request_timeout=10)[topic].result(15)
        if bucket_created:
            s3.delete_object(Bucket=bucket, Key='probe.txt')
            s3.delete_bucket(Bucket=bucket)
        if capture_bucket_created:
            if audio_key:
                s3.delete_object(Bucket=capture_bucket, Key=audio_key)
            s3.delete_bucket(Bucket=capture_bucket)
        if schema_created:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


if __name__ == '__main__':
    main()
