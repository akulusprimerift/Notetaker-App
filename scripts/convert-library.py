"""Maintenance-only PostgreSQL conversion. No legacy driver ships in the app."""
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from notetaker.library_conversion import convert_library
from notetaker.local_audio_store import LocalAudioStore


class LegacyObjects:
    def __init__(self):
        import boto3
        endpoint = os.environ['NOTETAKER_LEGACY_S3_ENDPOINT']
        if urlsplit(endpoint).hostname not in ('127.0.0.1', 'localhost'):
            raise ValueError('Use the earlier local audio service')
        self.bucket = os.environ.get('NOTETAKER_LEGACY_AUDIO_BUCKET', 'notetaker-audio')
        self.client = boto3.client('s3', endpoint_url=endpoint, region_name='us-east-1',
            aws_access_key_id=os.environ['NOTETAKER_LEGACY_S3_ACCESS_KEY'],
            aws_secret_access_key=os.environ['NOTETAKER_LEGACY_S3_SECRET_KEY'])

    def ready(self):
        self.client.head_bucket(Bucket=self.bucket)

    def list_keys(self, prefix):
        return [row['Key'] for page in self.client.get_paginator('list_objects_v2').paginate(Bucket=self.bucket, Prefix=prefix)
                for row in page.get('Contents', [])]

    def read(self, key):
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        with response['Body'] as stream:
            data = stream.read(8 * 1024 * 1024 + 1)
        if len(data) != response['ContentLength']:
            raise RuntimeError('An original audio object could not be read in full')
        return data


def main():
    parser = argparse.ArgumentParser(description='Convert the paused earlier library into a new verified SQLite folder.')
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--audio-directory', type=Path, help='Original local audio folder; omit for earlier SeaweedFS storage')
    parser.add_argument('--source-paused', action='store_true', required=True, help='Confirm recording and both inference workers are paused')
    args = parser.parse_args()
    url = make_url(os.environ['NOTETAKER_LEGACY_DATABASE_URL'])
    if url.drivername != 'postgresql+psycopg' or url.host not in ('127.0.0.1', 'localhost'):
        raise ValueError('Use the earlier local PostgreSQL server')
    source = create_engine(url, pool_pre_ping=True)
    try:
        report = convert_library(source, LocalAudioStore(args.audio_directory) if args.audio_directory else LegacyObjects(), args.destination)
        print('Converted and verified ' + str(sum(report['table_counts'].values())) + ' records and ' + str(len(report['audio_files'])) + ' audio files. Choose this SQLite folder in Notetaker setup.')
    finally:
        source.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Database URLs, source text and credentials must never be printed.
        raise SystemExit('Conversion failed. The original library is retained and the destination was not published. Inspect the staging folder or retry after checking source availability and schema.') from None
