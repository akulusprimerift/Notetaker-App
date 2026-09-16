"""Versioned spelling hints, never independent evidence of lecture content."""
import unicodedata
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from . import models as m
from .security import error


class TermsInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_version: int = Field(ge=0)
    terms: list[str] = Field(max_length=40)

    @field_validator('terms')
    @classmethod
    def bounded_terms(cls, terms):
        clean = [term.strip() for term in terms]
        if any(not term or len(term) > 60 or any(unicodedata.category(c).startswith('C') for c in term) for term in clean):
            raise ValueError('Use nonempty terms of at most 60 characters without control characters.')
        if sum(len(term) for term in clean) > 1000:
            raise ValueError('Use at most 1,000 characters in total.')
        if len({term.casefold() for term in clean}) != len(clean):
            raise ValueError('List each term only once.')
        return clean


def terms_json(row):
    return {'version_id': row.id, 'version': row.version, 'terms': row.terms} if row else {'version_id': None, 'version': 0, 'terms': []}


def latest_terms(db, course_id):
    return terms_json(db.scalar(select(m.CourseTerminology).where(m.CourseTerminology.course_id == course_id)
        .order_by(m.CourseTerminology.version.desc()).limit(1)))


def install_terminology(app, current, db_session, owned_course, receipt):
    @app.get('/courses/{course_id}/terminology')
    def get_terms(course_id: str, session=Depends(current), db=Depends(db_session)):
        owned_course(db, session.owner_id, course_id)
        return latest_terms(db, course_id)

    @app.post('/courses/{course_id}/terminology')
    def save_terms(course_id: str, body: TermsInput, request: Request, session=Depends(current), db=Depends(db_session)):
        action = 'course.terminology:' + course_id
        prior, key, fingerprint = receipt(db, request, session, action, body.model_dump())
        # receipt serializes owner mutations, including SQLite writes and course deletion.
        course = owned_course(db, session.owner_id, course_id)
        db.refresh(course, with_for_update=True)
        if course.tombstoned:
            error(404, 'unavailable', 'This course is unavailable.')
        if prior:
            return terms_json(db.get(m.CourseTerminology, prior.result_id))
        latest = latest_terms(db, course_id)
        if latest['version'] != body.expected_version:
            error(409, 'terminology_changed', 'Course terms changed in another window. Your draft is still here; load saved terms to compare.')
        row = m.CourseTerminology(course_id=course_id, version=latest['version'] + 1, terms=body.terms)
        db.add(row); db.flush()
        db.add(m.CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
        db.commit()
        return terms_json(row)
