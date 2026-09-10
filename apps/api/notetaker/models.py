from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, ForeignKey, ForeignKeyConstraint, UniqueConstraint, JSON, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    singleton: Mapped[int] = mapped_column(Integer, unique=True, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (CheckConstraint("singleton = 1", name="one_local_owner"),)


class Bootstrap(Base):
    __tablename__ = "bootstrap_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    token_hash: Mapped[str] = mapped_column(String(64))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    __table_args__ = (CheckConstraint("id = 1", name="one_bootstrap"),)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(24), default="")
    tombstoned: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("id", "owner_id"),)


class Lecture(Base):
    __tablename__ = "lectures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="prepared")
    lifecycle_epoch: Mapped[int] = mapped_column(Integer, default=1)
    audio_removed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    capture_epoch: Mapped[int] = mapped_column(Integer, default=0)
    audio_epoch: Mapped[int] = mapped_column(Integer, default=1)
    update_seq: Mapped[int] = mapped_column(Integer, default=0)
    tombstoned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SettingsVersion(Base):
    __tablename__ = "settings_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey("lectures.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    depth: Mapped[str] = mapped_column(String(20), default="detailed")
    format: Mapped[str] = mapped_column(String(24), default="topic_outline")
    ai_explanations: Mapped[bool] = mapped_column(Boolean, default=False)
    instructions: Mapped[str] = mapped_column(String(1000), default='', server_default='')
    detail_prompt: Mapped[str] = mapped_column(String(2000), default="", server_default="")
    layout_prompt: Mapped[str] = mapped_column(String(2000), default="", server_default="")
    material_ids: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')
    __table_args__ = (UniqueConstraint("lecture_id", "version"),)


class CourseMaterial(Base):
    __tablename__ = 'course_materials'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    lecture_id: Mapped[str | None] = mapped_column(ForeignKey('lectures.id'), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(24))
    sha256: Mapped[str] = mapped_column(String(64))
    original: Mapped[str] = mapped_column(Text)
    pages: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CommandReceipt(Base):
    __tablename__ = "command_receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"))
    action: Mapped[str] = mapped_column(String(120))
    key: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(64))
    result_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (UniqueConstraint("owner_id", "action", "key"),)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey("lectures.id"), index=True)
    logical_key: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="due", index=True)
    lifecycle_epoch: Mapped[int] = mapped_column(Integer)
    audio_epoch: Mapped[int | None] = mapped_column(Integer)
    input_revision: Mapped[str] = mapped_column(String(80))
    due_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    attempt_token: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_code: Mapped[str | None] = mapped_column(String(50))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Outbox(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey("lectures.id"))
    event_type: Mapped[str] = mapped_column(String(60))
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    entity_id: Mapped[str] = mapped_column(String(36))
    lifecycle_epoch: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class Inbox(Base):
    __tablename__ = "inbox_events"
    consumer: Mapped[str] = mapped_column(String(60), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class LectureUpdate(Base):
    __tablename__ = "lecture_updates"
    lecture_id: Mapped[str] = mapped_column(ForeignKey("lectures.id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36))
    entity_version: Mapped[int] = mapped_column(Integer)


class CaptureRun(Base):
    __tablename__ = "capture_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey("lectures.id"), index=True)
    capture_epoch: Mapped[int] = mapped_column(Integer)
    lifecycle_epoch: Mapped[int] = mapped_column(Integer)
    audio_epoch: Mapped[int] = mapped_column(Integer)
    grant_hash: Mapped[str] = mapped_column(String(64))
    grant_expires_at: Mapped[datetime] = mapped_column(DateTime)
    sample_rate: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20), default="recording")
    recovery: Mapped[bool] = mapped_column(Boolean, default=False)
    manifest_version: Mapped[int] = mapped_column(Integer, default=0)
    last_sequence: Mapped[int | None] = mapped_column(Integer)
    final_sample_count: Mapped[int | None] = mapped_column(BigInteger)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("id", "lecture_id"), UniqueConstraint("lecture_id", "capture_epoch"),
        CheckConstraint("sample_rate >= 8000 AND sample_rate <= 192000", name="capture_sample_rate"))


class UploadReservation(Base):
    __tablename__ = "upload_reservations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int] = mapped_column(Integer)
    identity: Mapped[dict] = mapped_column(JSON)
    object_key: Mapped[str] = mapped_column(String(240), unique=True)
    state: Mapped[str] = mapped_column(String(20), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (ForeignKeyConstraint(["run_id", "lecture_id"], ["capture_runs.id", "capture_runs.lecture_id"]),
        UniqueConstraint("run_id", "sequence"), UniqueConstraint("id", "lecture_id"),
        CheckConstraint("sequence >= 0", name="reservation_sequence"))


class AudioChunk(Base):
    __tablename__ = "audio_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lecture_id: Mapped[str] = mapped_column(String(36), index=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (ForeignKeyConstraint(["id", "lecture_id"], ["upload_reservations.id", "upload_reservations.lecture_id"]),)


class AudioManifestRevision(Base):
    __tablename__ = "audio_manifest_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36))
    run_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (ForeignKeyConstraint(["run_id", "lecture_id"], ["capture_runs.id", "capture_runs.lecture_id"]), UniqueConstraint("run_id", "version"))


class SpeechWindow(Base):
    __tablename__ = "speech_windows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(String(36))
    manifest_version: Mapped[int] = mapped_column(Integer)
    core_start: Mapped[int] = mapped_column(BigInteger)
    core_end: Mapped[int] = mapped_column(BigInteger)
    context_start: Mapped[int] = mapped_column(BigInteger)
    context_end: Mapped[int] = mapped_column(BigInteger)
    live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    outcome: Mapped[str | None] = mapped_column(String(20))
    preview: Mapped[str] = mapped_column(Text, default='', server_default='')
    preview_attempt: Mapped[str] = mapped_column(String(36), default='', server_default='')
    __table_args__ = (ForeignKeyConstraint(["run_id", "lecture_id"], ["capture_runs.id", "capture_runs.lecture_id"]),
        UniqueConstraint("id", "lecture_id"), UniqueConstraint("run_id", "manifest_version", "core_start"),
        CheckConstraint("context_start <= core_start AND core_start < core_end AND core_end <= context_end", name="speech_window_bounds"))


class SpeechGeneration(Base):
    __tablename__ = "speech_generations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36))
    window_id: Mapped[str] = mapped_column(String(36))
    attempt_token: Mapped[str] = mapped_column(String(36), unique=True)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (ForeignKeyConstraint(["window_id", "lecture_id"], ["speech_windows.id", "speech_windows.lecture_id"]), UniqueConstraint("id", "lecture_id"))


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36))
    window_id: Mapped[str] = mapped_column(String(36))
    position: Mapped[int] = mapped_column(Integer)
    current_revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (ForeignKeyConstraint(["window_id", "lecture_id"], ["speech_windows.id", "speech_windows.lecture_id"]),
        UniqueConstraint("id", "lecture_id"), UniqueConstraint("window_id", "position"))


class TranscriptVersion(Base):
    __tablename__ = "transcript_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36))
    segment_id: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(12000))
    author: Mapped[str] = mapped_column(String(20))
    start_sample: Mapped[int] = mapped_column(BigInteger)
    end_sample: Mapped[int] = mapped_column(BigInteger)
    confidence: Mapped[dict] = mapped_column(JSON)
    generation_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (ForeignKeyConstraint(["segment_id", "lecture_id"], ["transcript_segments.id", "transcript_segments.lecture_id"]),
        ForeignKeyConstraint(["generation_id", "lecture_id"], ["speech_generations.id", "speech_generations.lecture_id"]),
        UniqueConstraint("id", "lecture_id"), UniqueConstraint("segment_id", "revision"),
        CheckConstraint("start_sample >= 0 AND end_sample > start_sample", name="transcript_span"))


class TranscriptSnapshot(Base):
    __tablename__ = "transcript_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey("lectures.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    audio_epoch: Mapped[int] = mapped_column(Integer)
    stability: Mapped[str] = mapped_column(String(20), default="stable", server_default="stable")
    manifests: Mapped[list] = mapped_column(JSON)
    issues: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("id", "lecture_id"), UniqueConstraint("lecture_id", "sequence"))


class TranscriptSnapshotItem(Base):
    __tablename__ = "transcript_snapshot_items"
    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    lecture_id: Mapped[str] = mapped_column(String(36))
    version_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (ForeignKeyConstraint(["snapshot_id", "lecture_id"], ["transcript_snapshots.id", "transcript_snapshots.lecture_id"]),
        ForeignKeyConstraint(["version_id", "lecture_id"], ["transcript_versions.id", "transcript_versions.lecture_id"]))


class NotePreference(Base):
    __tablename__ = 'note_preferences'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey('lectures.id'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(160))
    model_digest: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('lecture_id', 'version'), UniqueConstraint('id', 'lecture_id'))


class NoteRequest(Base):
    __tablename__ = 'note_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36), index=True)
    preference_id: Mapped[str] = mapped_column(String(36))
    snapshot_id: Mapped[str] = mapped_column(String(36))
    settings_id: Mapped[str] = mapped_column(ForeignKey('settings_versions.id'))
    base_revision: Mapped[int] = mapped_column(Integer)
    source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preview: Mapped[str] = mapped_column(Text, default='', server_default='')
    preview_attempt: Mapped[str] = mapped_column(String(36), default='', server_default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('id', 'lecture_id'),
        UniqueConstraint('snapshot_id', 'preference_id', 'settings_id', 'base_revision', name='uq_note_request_batch'),
        ForeignKeyConstraint(['snapshot_id', 'lecture_id'], ['transcript_snapshots.id', 'transcript_snapshots.lecture_id']),
        ForeignKeyConstraint(['preference_id', 'lecture_id'], ['note_preferences.id', 'note_preferences.lecture_id']))


class NoteRevision(Base):
    __tablename__ = 'note_revisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    revision: Mapped[int] = mapped_column(Integer)
    attempt_token: Mapped[str] = mapped_column(String(36), unique=True)
    content: Mapped[dict] = mapped_column(JSON)
    resolved_citations: Mapped[list] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('lecture_id', 'revision'),
        ForeignKeyConstraint(['request_id', 'lecture_id'], ['note_requests.id', 'note_requests.lecture_id']))


class NoteEdit(Base):
    """Immutable selected student revision; automatic output is kept separately."""
    __tablename__ = 'note_edits'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey('lectures.id'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    generated_id: Mapped[str] = mapped_column(ForeignKey('note_revisions.id'))
    reviewed_id: Mapped[str] = mapped_column(ForeignKey('note_revisions.id'))
    content: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[list] = mapped_column(JSON)
    action: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('lecture_id', 'version'),)


class PromptProfile(Base):
    __tablename__ = 'prompt_profiles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    detail_prompt: Mapped[str] = mapped_column(String(2000), default='')
    layout_prompt: Mapped[str] = mapped_column(String(2000), default='')
    instructions: Mapped[str] = mapped_column(String(1000), default='')
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class Finalization(Base):
    __tablename__ = 'finalizations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey('lectures.id'), index=True)
    lifecycle_epoch: Mapped[int] = mapped_column(Integer)
    audio_epoch: Mapped[int] = mapped_column(Integer)
    expected_edit_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default='speech')
    issues: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FinalSnapshot(Base):
    __tablename__ = 'final_snapshots'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey('lectures.id'), index=True)
    finalization_id: Mapped[str] = mapped_column(ForeignKey('finalizations.id'), unique=True)
    content: Mapped[dict] = mapped_column(JSON)
    markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Deletion(Base):
    __tablename__ = 'deletions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lecture_id: Mapped[str] = mapped_column(ForeignKey('lectures.id'), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    lifecycle_epoch: Mapped[int] = mapped_column(Integer)
    audio_epoch: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default='deleting')
    error: Mapped[str | None] = mapped_column(String(100))
    browser_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime)


class DeletionObject(Base):
    __tablename__ = 'deletion_objects'
    deletion_id: Mapped[str] = mapped_column(ForeignKey('deletions.id'), primary_key=True)
    object_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    removed: Mapped[bool] = mapped_column(Boolean, default=False)
