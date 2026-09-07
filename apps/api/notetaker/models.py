from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, ForeignKey, ForeignKeyConstraint, UniqueConstraint, JSON, CheckConstraint
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("id", "owner_id"),)


class Lecture(Base):
    __tablename__ = "lectures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="prepared")
    lifecycle_epoch: Mapped[int] = mapped_column(Integer, default=1)
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
    __table_args__ = (UniqueConstraint("lecture_id", "version"),)


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
