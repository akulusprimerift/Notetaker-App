import json
import logging
import secrets
from time import perf_counter
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

from fastapi import FastAPI, Depends, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update, text, func
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings
from .db import database
from .models import Bootstrap, Owner, Session, Course, Lecture, SettingsVersion, CommandReceipt, Outbox, LectureUpdate, Job, now
from .security import authenticate, mutation, digest, error
from .audio_store import AudioStore
from .capture import install_capture
from .transcription import install_transcription, transcript_json
from .notes import install_notes, notes_json

log = logging.getLogger("notetaker")


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BootstrapInput(StrictInput):
    token: str = Field(min_length=32, max_length=200)


class CourseInput(StrictInput):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(default="", max_length=24)


class LectureInput(StrictInput):
    title: str = Field(min_length=1, max_length=160)


def course_json(course):
    return {"id": course.id, "name": course.name, "code": course.code, "created_at": course.created_at.isoformat() + "Z"}


def lecture_json(lecture):
    return {"id": lecture.id, "course_id": lecture.course_id, "title": lecture.title, "status": lecture.status,
            "created_at": lecture.created_at.isoformat() + "Z", "update_cursor": lecture.update_seq}


def owned_course(db, owner, course_id):
    course = db.scalar(select(Course).where(Course.id == course_id, Course.owner_id == owner))
    if not course:
        error(404, "unavailable", "This course is unavailable.")
    return course


def owned_lecture(db, owner, lecture_id):
    lecture = db.scalar(select(Lecture).join(Course).where(Lecture.id == lecture_id, Course.owner_id == owner, Lecture.tombstoned.is_(False)))
    if not lecture:
        error(404, "unavailable", "This lecture is unavailable.")
    return lecture


def receipt(db, request, session, action, payload):
    mutation(request, session)
    key = request.headers.get("idempotency-key", "")
    if not 8 <= len(key) <= 80:
        error(422, "idempotency_key_required", "A valid request identifier is required.")
    fingerprint = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    # Serializes command receipts for this owner, including concurrent identical requests.
    # SQLite has no row-level FOR UPDATE; preview uses a write lock instead.
    if db.bind.dialect.name == "sqlite":
        db.execute(update(Owner).where(Owner.id == session.owner_id).values(singleton=1))
    else:
        db.scalar(select(Owner).where(Owner.id == session.owner_id).with_for_update())
    existing = db.scalar(select(CommandReceipt).where(CommandReceipt.owner_id == session.owner_id, CommandReceipt.action == action, CommandReceipt.key == key))
    if existing and existing.fingerprint != fingerprint:
        error(409, "idempotency_conflict", "This request identifier was already used for different content.")
    return existing, key, fingerprint


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    engine, sessions = database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="Notetaker API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings, app.state.engine, app.state.sessions = settings, engine, sessions
    app.state.audio_store = AudioStore(settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.middleware("http")
    async def trace(request: Request, call_next):
        started=perf_counter()
        request.state.trace_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Server-Timing"] = f"api;dur={(perf_counter()-started)*1000:.1f}"
        # Route templates contain no course names, text, query strings or credentials.
        route=getattr(request.scope.get('route'),'path','unmatched')
        log.info('request trace_id=%s route=%s status=%s elapsed_ms=%.1f',request.state.trace_id,route,response.status_code,(perf_counter()-started)*1000)
        return response

    @app.exception_handler(HTTPException)
    async def api_error(request, exc):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code":"request_failed", "message":"The request could not be completed.", "retryable":False}
        return JSONResponse({"error":detail, "trace_id":getattr(request.state,"trace_id",None)}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo rejected lecture text, bootstrap tokens or raw validation inputs.
        return JSONResponse({"error":{"code":"invalid_input","message":"Check the required fields and their length.","retryable":False},"trace_id":request.state.trace_id},status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(request, exc):
        log.error("storage_failure trace_id=%s", request.state.trace_id)
        return JSONResponse({"error":{"code":"storage_unavailable","message":"Storage is unavailable. Your form is still here; try again.","retryable":True},"trace_id":request.state.trace_id}, status_code=503)

    def db_session():
        with sessions() as db:
            yield db

    def current(request: Request, db=Depends(db_session)):
        return authenticate(db, request.cookies.get("nt_session"))

    @app.get("/health")
    def health():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM alembic_version"))
            return {"status":"ok"}
        except SQLAlchemyError:
            return JSONResponse({"status":"unavailable"}, status_code=503)

    @app.post("/session/bootstrap")
    def bootstrap(body: BootstrapInput, request: Request, response: Response, db=Depends(db_session)):
        mutation(request)
        consumed = db.execute(update(Bootstrap).where(Bootstrap.id==1, Bootstrap.used.is_(False), Bootstrap.token_hash==digest(body.token), Bootstrap.expires_at>now()).values(used=True))
        if consumed.rowcount != 1:
            error(401, "setup_code_invalid", "This setup code is invalid, expired or already used. Run the local unlock command for a new code.")
        owner = db.scalar(select(Owner))
        if not owner:
            owner=Owner()
            db.add(owner)
            db.flush()
        token=secrets.token_urlsafe(48)
        csrf=digest("csrf:"+token)
        db.add(Session(token_hash=digest(token),owner_id=owner.id,csrf_hash=digest(csrf),expires_at=now()+timedelta(hours=settings.session_hours)))
        db.commit()
        response.set_cookie("nt_session",token,httponly=True,secure=settings.secure_cookies,samesite="strict",max_age=settings.session_hours*3600,path="/")
        return {"csrf_token":csrf,"preview":settings.preview,"owner_id":owner.id}

    @app.get("/session")
    def session_info(request: Request, session=Depends(current)):
        return {"csrf_token":digest("csrf:"+request.cookies["nt_session"]),"preview":settings.preview,"owner_id":session.owner_id}

    @app.post("/session/logout",status_code=204)
    def logout(request: Request,response: Response,session=Depends(current),db=Depends(db_session)):
        mutation(request,session)
        session.revoked=True
        db.commit()
        response.delete_cookie("nt_session",path="/")

    @app.get("/courses")
    def courses(session=Depends(current),db=Depends(db_session)):
        rows=db.scalars(select(Course).where(Course.owner_id==session.owner_id).order_by(Course.created_at,Course.id)).all()
        return [course_json(row) for row in rows]

    @app.post("/courses",status_code=201)
    def create_course(body: CourseInput,request: Request,session=Depends(current),db=Depends(db_session)):
        existing,key,fingerprint=receipt(db,request,session,"create_course",body.model_dump())
        if existing:
            return course_json(owned_course(db,session.owner_id,existing.result_id))
        course=Course(owner_id=session.owner_id,**body.model_dump())
        db.add(course)
        db.flush()
        db.add(CommandReceipt(owner_id=session.owner_id,action="create_course",key=key,fingerprint=fingerprint,result_id=course.id))
        db.commit()
        return course_json(course)

    @app.get("/courses/{course_id}/lectures")
    def lectures(course_id: str,session=Depends(current),db=Depends(db_session)):
        owned_course(db,session.owner_id,course_id)
        return [lecture_json(row) for row in db.scalars(select(Lecture).where(Lecture.course_id==course_id,Lecture.tombstoned.is_(False)).order_by(Lecture.created_at.desc(),Lecture.id))]

    @app.post("/courses/{course_id}/lectures",status_code=201)
    def create_lecture(course_id: str,body: LectureInput,request: Request,session=Depends(current),db=Depends(db_session)):
        owned_course(db,session.owner_id,course_id)
        action="create_lecture:"+course_id
        existing,key,fingerprint=receipt(db,request,session,action,body.model_dump())
        if existing:
            return lecture_json(owned_lecture(db,session.owner_id,existing.result_id))
        lecture=Lecture(course_id=course_id,title=body.title,update_seq=1)
        db.add(lecture)
        db.flush()
        db.add_all([
            SettingsVersion(lecture_id=lecture.id),
            CommandReceipt(owner_id=session.owner_id,action=action,key=key,fingerprint=fingerprint,result_id=lecture.id),
            LectureUpdate(lecture_id=lecture.id,sequence=1,kind="lecture.created",entity_id=lecture.id,entity_version=1),
            Outbox(lecture_id=lecture.id,event_type="lecture.created",entity_id=lecture.id,lifecycle_epoch=1),
        ])
        db.commit()
        return lecture_json(lecture)

    @app.get("/lectures/{lecture_id}/snapshot")
    def snapshot(lecture_id: str,session=Depends(current),db=Depends(db_session)):
        # One joined read keeps lecture/settings/cursor consistent even at READ COMMITTED.
        newest_settings=select(func.max(SettingsVersion.version)).where(SettingsVersion.lecture_id==Lecture.id).correlate(Lecture).scalar_subquery()
        row=db.execute(select(Lecture,SettingsVersion,Course.name).join(Course).join(SettingsVersion,SettingsVersion.lecture_id==Lecture.id).where(Lecture.id==lecture_id,Course.owner_id==session.owner_id,Lecture.tombstoned.is_(False),SettingsVersion.version==newest_settings)).first()
        if not row:
            error(404,"unavailable","This lecture is unavailable.")
        lecture,prefs,course_name=row
        return {"lecture":lecture_json(lecture),"course_name":course_name,"settings":{"depth":prefs.depth,"format":prefs.format,"ai_explanations":prefs.ai_explanations,"version":prefs.version},
                "capture":{"status":"not_started" if lecture.status=='prepared' else lecture.status,"available":app.state.audio_store.available},"transcript":transcript_json(db,lecture),"notes":notes_json(db,lecture),"processing_location":"local","update_cursor":lecture.update_seq}

    @app.get("/lectures/{lecture_id}/audio/{version}")
    def unavailable_source(lecture_id: str,version: str,session=Depends(current),db=Depends(db_session)):
        owned_lecture(db,session.owner_id,lecture_id)
        error(404,"source_unavailable","No source has been captured for this lecture.")

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str,session=Depends(current),db=Depends(db_session)):
        job=db.get(Job,job_id)
        if not job:
            error(404,"unavailable","This job is unavailable.")
        owned_lecture(db,session.owner_id,job.lecture_id)
        return {"id":job.id,"status":job.status,"error_code":job.error_code}

    @app.websocket("/lectures/{lecture_id}/updates")
    async def updates(socket: WebSocket,lecture_id: str):
        # M01 provides authenticated snapshot notification, not the M05 replay stream.
        try:
            if socket.headers.get("origin") != settings.web_origin:
                raise HTTPException(403)
            with sessions() as db:
                session=authenticate(db,socket.cookies.get("nt_session"))
                owned_lecture(db,session.owner_id,lecture_id)
            await socket.accept()
            await socket.send_json({"kind":"snapshot_required","lecture_id":lecture_id})
            await socket.close(code=1000)
        except HTTPException:
            await socket.close(code=1008)
        except WebSocketDisconnect:
            pass

    install_capture(app, current, db_session, owned_lecture, receipt)
    install_transcription(app, current, db_session, owned_lecture, receipt)
    install_notes(app, current, db_session, owned_lecture, receipt)
    return app


app=create_app()
