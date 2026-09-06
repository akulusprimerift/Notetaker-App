"""Explicit integration probe; owns only its freshly generated verification object/topic."""
import hashlib
import json
import os
import time
from uuid import uuid4
import boto3
from botocore.config import Config
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic
from sqlalchemy import text
from .config import Settings
from .db import database


def main():
    settings=Settings()
    if settings.preview:
        raise RuntimeError('Real service verification requires PostgreSQL mode')
    engine,_=database(settings.database_url)
    with engine.connect() as connection:
        version=connection.execute(text('SELECT version()')).scalar_one()
    engine.dispose()
    suffix=uuid4().hex
    bucket='notetaker-verify-'+suffix
    payload=b'Notetaker synthetic service verification, no lecture content.'
    s3=boto3.client('s3',endpoint_url=os.environ.get('S3_ENDPOINT','http://127.0.0.1:8333'),aws_access_key_id=os.environ['S3_ACCESS_KEY'],aws_secret_access_key=os.environ['S3_SECRET_KEY'],region_name='us-east-1',config=Config(signature_version='s3v4',s3={'addressing_style':'path'},connect_timeout=5,read_timeout=5,retries={'max_attempts':1}))
    s3.create_bucket(Bucket=bucket)
    try:
        s3.put_object(Bucket=bucket,Key='probe.txt',Body=payload)
        actual=s3.get_object(Bucket=bucket,Key='probe.txt')['Body'].read()
        assert len(actual)==len(payload) and hashlib.sha256(actual).digest()==hashlib.sha256(payload).digest()
    finally:
        s3.delete_object(Bucket=bucket,Key='probe.txt')
        s3.delete_bucket(Bucket=bucket)
    address=os.environ.get('KAFKA_BOOTSTRAP','127.0.0.1:9092')
    topic='notetaker.verify.'+suffix
    admin=AdminClient({'bootstrap.servers':address})
    admin.create_topics([NewTopic(topic,num_partitions=1,replication_factor=1)],request_timeout=10)[topic].result(15)
    consumer=None
    try:
        producer=Producer({'bootstrap.servers':address,'message.timeout.ms':10000,'acks':'all'})
        failures=[]
        producer.produce(topic,key=suffix,value=json.dumps({'event_id':suffix,'kind':'verification'}),on_delivery=lambda err,_:failures.append(str(err)) if err else None)
        assert producer.flush(15)==0 and not failures
        consumer=Consumer({'bootstrap.servers':address,'group.id':topic,'auto.offset.reset':'earliest','enable.auto.commit':False})
        consumer.subscribe([topic])
        deadline=time.monotonic()+20
        message=None
        while time.monotonic()<deadline:
            candidate=consumer.poll(1)
            if candidate and not candidate.error():message=candidate;break
        assert message is not None and json.loads(message.value())['event_id']==suffix
        consumer.commit(message=message,asynchronous=False)
    finally:
        if consumer:consumer.close()
        admin.delete_topics([topic],request_timeout=10)[topic].result(15)
    print(json.dumps({'postgres':version,'object_readback':'passed','kafka_roundtrip':'passed','scope':'synthetic service probe; not capture durability'},indent=2))


if __name__=='__main__':main()
