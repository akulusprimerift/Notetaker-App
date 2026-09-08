"""Private object storage. No object URL or credential is returned to the browser."""
import hashlib
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class AudioStore:
    def __init__(self, settings):
        self.available = bool(settings.s3_access_key and settings.s3_secret_key and not settings.preview)
        self.bucket = settings.audio_bucket
        self.client = boto3.client('s3', endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key, aws_secret_access_key=settings.s3_secret_key,
            region_name='us-east-1', config=Config(signature_version='s3v4', s3={'addressing_style':'path'},
                connect_timeout=3, read_timeout=10, retries={'max_attempts':1})) if self.available else None

    def ready(self):
        if not self.available:
            raise RuntimeError('audio_store_unconfigured')
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if exc.response['ResponseMetadata']['HTTPStatusCode'] != 404:
                raise
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except ClientError as create_error:
                if create_error.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
                    raise

    def write_verified(self, key, data, checksum):
        # Reservation identity includes SHA-256 before any write. A retry to this key
        # must contain the same verified bytes; it cannot replace another identity.
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType='audio/wav')
        actual = self.read(key)
        if len(actual) != len(data) or hashlib.sha256(actual).hexdigest() != checksum:
            raise RuntimeError('audio_readback_mismatch')

    def read(self, key):
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        with response['Body'] as stream:
            return stream.read(8 * 1024 * 1024 + 1)


    def list_keys(self, prefix):
        self.ready()
        keys=[]
        for page in self.client.get_paginator('list_objects_v2').paginate(Bucket=self.bucket,Prefix=prefix):
            keys.extend(row['Key'] for row in page.get('Contents',[]))
        return keys

    def delete_verified(self, key):
        self.client.delete_object(Bucket=self.bucket,Key=key)
        try:
            self.client.head_object(Bucket=self.bucket,Key=key)
        except ClientError as exc:
            if exc.response['ResponseMetadata']['HTTPStatusCode']==404:return
            raise
        raise RuntimeError('object_still_present')
