from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from notetaker.db import database
from notetaker.backup_sqlite import backup_database
from notetaker.models import (AudioManifestRevision, CaptureRun, CommandReceipt, Course, Deletion,
    DeletionObject, Finalization, FinalSnapshot, Inbox, Job, Lecture, NoteEdit, NotePreference,
    NoteRequest, NoteRevision, Outbox, Owner, SettingsVersion, TranscriptSnapshot)
from notetaker.postgres_migration import migrate_database


def _upgrade(engine, root, revision='head'):
    with engine.begin() as connection:
        config = Config(str(root / 'alembic.ini'))
        config.attributes['connection'] = connection
        command.upgrade(config, revision)


def test_staged_migration_preserves_ids_revisions_retention_and_recovery(tmp_path):
    root = __import__('pathlib').Path(__file__).resolve().parents[3]
    source_path = tmp_path / 'source.sqlite3'
    source_url = URL.create('sqlite', database=str(source_path)).render_as_string(hide_password=False)
    source_engine, _ = database(source_url)
    _upgrade(source_engine, root)
    stamp = datetime(2026, 4, 5, 6, 7, 8, 90123)
    owner_id, course_id, lecture_id = str(uuid4()), str(uuid4()), str(uuid4())
    settings_id, snapshot_id = str(uuid4()), str(uuid4())
    preference_id, request_id, note_id = str(uuid4()), str(uuid4()), str(uuid4())
    run_id, manifest_id, finalization_id = str(uuid4()), str(uuid4()), str(uuid4())
    final_snapshot_id, deletion_id = str(uuid4()), str(uuid4())
    job_id, outbox_id, receipt_id = str(uuid4()), str(uuid4()), str(uuid4())
    attempt_token = str(uuid4())
    with Session(source_engine) as db:
        db.add(Owner(id=owner_id, singleton=1, created_at=stamp))
        db.commit()
        db.add(Course(id=course_id, owner_id=owner_id, name='Synthetic chemistry', code='SYN', created_at=stamp))
        db.commit()
        db.add(Lecture(id=lecture_id, course_id=course_id, title='Retention boundary', created_at=stamp,
            audio_removed=True, keep_audio=False, audio_epoch=3, update_seq=5))
        db.commit()
        db.add(CaptureRun(id=run_id, lecture_id=lecture_id, capture_epoch=1, lifecycle_epoch=2,
            audio_epoch=3, grant_hash='g'*64, grant_expires_at=stamp+timedelta(minutes=10),
            sample_rate=48000, state='sealed', recovery=False, manifest_version=7,
            last_sequence=1, final_sample_count=96000, gaps=[], released_through=96000,
            created_at=stamp, heartbeat_at=stamp))
        db.commit()
        db.add_all([
            SettingsVersion(id=settings_id, lecture_id=lecture_id, version=2, depth='detailed',
                format='topic_outline', ai_explanations=False, instructions='preserve equations',
                detail_prompt='explain every step', layout_prompt='ordered outline', material_ids=['material-1']),
            TranscriptSnapshot(id=snapshot_id, lecture_id=lecture_id, sequence=4, audio_epoch=3,
                stability='final', manifests=[{'run_id':run_id,'version':7}], issues=[], created_at=stamp),
            NotePreference(id=preference_id, lecture_id=lecture_id, version=1, model='local-test',
                model_digest='d'*64, enabled=True, created_at=stamp),
            AudioManifestRevision(id=manifest_id, lecture_id=lecture_id, run_id=run_id, version=7,
                content={'released_through':96000,'chunks':[]}, created_at=stamp),
            Finalization(id=finalization_id, lecture_id=lecture_id, lifecycle_epoch=2, audio_epoch=3,
                expected_edit_version=1, status='complete', issues=[], discard_audio=True, created_at=stamp),
            Deletion(id=deletion_id, lecture_id=lecture_id, owner_id=owner_id, kind='audio',
                lifecycle_epoch=2, audio_epoch=3, status='reconciling', browser_ack=False,
                created_at=stamp, reconciled_at=None),
            Job(id=job_id, lecture_id=lecture_id, logical_key='speech:synthetic:1', kind='speech.window',
                status='running', lifecycle_epoch=2, audio_epoch=3, input_revision='manifest:7',
                due_at=stamp, attempt_token=attempt_token, lease_expires_at=stamp+timedelta(minutes=2),
                error_code=None, attempts=2),
            Outbox(id=outbox_id, lecture_id=lecture_id, event_type='speech.window', schema_version=1,
                entity_id=job_id, lifecycle_epoch=2, created_at=stamp, published_at=None),
            Inbox(consumer='synthetic-consumer', event_id=outbox_id, processed_at=stamp),
            CommandReceipt(id=receipt_id, owner_id=owner_id, action='lecture.create', key='retry-key',
                fingerprint='f'*64, result_id=lecture_id),
        ])
        db.commit()
        db.add_all([
            NoteRequest(id=request_id, lecture_id=lecture_id, preference_id=preference_id,
                snapshot_id=snapshot_id, settings_id=settings_id, base_revision=2,
                source_ids=['source-1'], created_at=stamp),
            NoteRevision(id=note_id, lecture_id=lecture_id, request_id=request_id, revision=3,
                attempt_token=attempt_token, content={'blocks':[{'id':'immutable-1','text':'A retained fact.'}]},
                resolved_citations=[{'source_id':'source-1','start_sample':12}],
                metadata_json={'model':'local-test','quality':'synthetic'}, created_at=stamp),
        ])
        db.commit()
        db.add_all([
            NoteEdit(id=str(uuid4()), lecture_id=lecture_id, version=1, generated_id=note_id,
                reviewed_id=note_id, content={'blocks':[{'id':'student-1','text':'My saved correction.'}]},
                provenance=[{'author':'student'}], action='save', created_at=stamp),
            FinalSnapshot(id=final_snapshot_id, lecture_id=lecture_id, finalization_id=finalization_id,
                content={'revision_id':note_id}, markdown='# Retained final snapshot', created_at=stamp),
            DeletionObject(deletion_id=deletion_id, object_key='synthetic/audio/object.wav', removed=False),
        ])
        db.commit()

    target_path = tmp_path / 'converted.sqlite3'
    result = migrate_database(source_engine, target_path)
    assert result['source_revision'] == result['destination_revision']
    assert result['tables']['note_revisions'] == 1
    assert result['tables']['deletion_objects'] == 1
    target_engine, _ = database(URL.create('sqlite', database=str(target_path)).render_as_string(hide_password=False))
    with target_engine.connect() as connection:
        assert connection.exec_driver_sql('PRAGMA integrity_check').scalar_one() == 'ok'
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
    with Session(target_engine) as migrated:
        assert migrated.execute(select(NoteRevision.id, NoteRevision.content, NoteRevision.created_at)).one() == (
            note_id, {'blocks':[{'id':'immutable-1','text':'A retained fact.'}]}, stamp)
        lecture = migrated.get(Lecture, lecture_id)
        assert lecture.audio_removed and not lecture.keep_audio and lecture.audio_epoch == 3
        finalization = migrated.get(Finalization, finalization_id)
        assert finalization.discard_audio and finalization.expected_edit_version == 1
        deletion = migrated.get(Deletion, deletion_id)
        assert deletion.status == 'reconciling' and not deletion.browser_ack and deletion.reconciled_at is None
        job = migrated.get(Job, job_id)
        assert job.attempt_token == attempt_token and job.lease_expires_at == stamp+timedelta(minutes=2)
        assert migrated.execute(select(CommandReceipt.result_id).where(CommandReceipt.id == receipt_id)).scalar_one() == lecture_id
        assert migrated.execute(text('SELECT count(*) FROM outbox_events')).scalar_one() == 1
        assert migrated.execute(text('SELECT count(*) FROM inbox_events')).scalar_one() == 1
    target_engine.dispose()

    backup_path = tmp_path / 'verified-backup.sqlite3'
    assert backup_database(target_path, backup_path) == backup_path
    backup_engine, _ = database(URL.create('sqlite', database=str(backup_path)).render_as_string(hide_password=False))
    with backup_engine.connect() as connection:
        assert connection.execute(select(NoteRevision.id)).scalar_one() == note_id
        assert connection.exec_driver_sql('PRAGMA integrity_check').scalar_one() == 'ok'
    backup_engine.dispose()

    existing_path = tmp_path / 'existing.sqlite3'
    existing_path.write_bytes(b'keep this destination')
    with pytest.raises(FileExistsError):
        migrate_database(source_engine, existing_path)
    assert existing_path.read_bytes() == b'keep this destination'
    source_engine.dispose()
