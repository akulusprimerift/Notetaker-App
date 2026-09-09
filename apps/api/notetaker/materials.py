"""Local, immutable course evidence. Uploaded content never has tool authority."""
import base64
import hashlib
import io
import re
import posixpath
import zipfile
import subprocess
import sys
import json
from pathlib import PurePosixPath
from typing import Literal
from xml.etree import ElementTree as ET
from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, or_, update
from .models import CourseMaterial, Course, Lecture, SettingsVersion, CommandReceipt, Job
from .security import error

MAX_BYTES = 8 * 1024 * 1024


def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('unsafe_xml')
    return ET.fromstring(data)


def extract(name, raw):
    extension = PurePosixPath(name).suffix.lower()
    pages = []
    if extension in ('.txt', '.md'):
        pages = [('Document', raw.decode('utf-8-sig'))]
    elif extension == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) > 300:
            raise ValueError('pdf_limit')
        for index, page in enumerate(reader.pages):
            pages.append((f'Page {index+1}', page.extract_text() or ''))
            if sum(len(text) for _, text in pages) > 180000:
                raise ValueError('text_limit')
    elif extension in ('.pptx', '.docx'):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 3000 or sum(e.file_size for e in entries) > 40 * 1024 * 1024:
                raise ValueError('archive_limit')
            if len({e.filename for e in entries}) != len(entries):
                raise ValueError('duplicate_entries')
            if extension == '.pptx':
                # Presentation order is defined by relationships, not slide filenames.
                presentation = xml(archive.read('ppt/presentation.xml'))
                relationships = xml(archive.read('ppt/_rels/presentation.xml.rels'))
                targets = {r.attrib['Id']: posixpath.normpath('ppt/'+r.attrib['Target'])
                    for r in relationships if r.attrib.get('TargetMode') != 'External'}
                selected = [targets[n.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
                    for n in presentation.iter() if n.tag.endswith('}sldId')]
                if any(not re.fullmatch(r'ppt/slides/[^/]+\.xml', n) for n in selected):
                    raise ValueError('invalid_slide_target')
            else:
                selected = ['word/document.xml']
            for index, entry in enumerate(selected):
                data = archive.read(entry)
                root = xml(data)
                paragraphs = [' '.join(n.text or '' for n in p.iter() if n.tag.endswith('}t'))
                    for p in root.iter() if p.tag.endswith('}p')]
                pages.append((f'Slide {index+1}' if extension == '.pptx' else 'Document', '\n'.join(paragraphs)))
    else:
        raise ValueError('unsupported_format')
    if len(pages) > 300 or sum(len(text) for _, text in pages) > 180000:
        raise ValueError('text_limit')
    if not any(text.strip() for _, text in pages):
        raise ValueError('no_readable_text')
    # Stable excerpts keep long document paragraphs within the note context budget.
    return [{'label': label + (f' · excerpt {start//3000+1}' if len(text)>3000 else ''),
        'text': text[start:start+3000].strip()} for label, text in pages for start in range(0, max(1, len(text)), 3000)]


def parse_upload(name, raw):
    # Keep malformed document processing out of the API process and bound runtime.
    try:
        result = subprocess.run([sys.executable, '-m', 'notetaker.material_parser', PurePosixPath(name).suffix.lower()],
            input=raw, capture_output=True, timeout=20, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        if result.returncode or len(result.stdout) > 1500000: raise ValueError('parse_failed')
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, OSError):
        raise ValueError('parse_failed') from None


def material_sources(db, ids):
    sources = []
    for ident in ids:
        row = db.get(CourseMaterial, ident)
        if not row:
            raise ValueError('material_missing')
        for index, page in enumerate(row.pages):
            if page['text']:
                sources.append({'id': f'material:{row.id}:{index}', 'text': page['text'],
                    'source_kind': row.kind, 'label': row.name + ' · ' + page['label']})
    return sources


def course_ids(db, course_id):
    return list(db.scalars(select(CourseMaterial.id).where(CourseMaterial.course_id == course_id,
        CourseMaterial.lecture_id.is_(None)).order_by(CourseMaterial.created_at, CourseMaterial.id)))


def source_for_lecture(db, lecture, source_id):
    pieces = source_id.split(':')
    if len(pieces) != 3:
        error(404, 'source_unavailable', 'This material source is unavailable.')
    row = db.get(CourseMaterial, pieces[1])
    if not row or row.course_id != lecture.course_id or row.lecture_id not in (None, lecture.id):
        error(404, 'source_unavailable', 'This material source is unavailable.')
    try:
        index = int(pieces[2])
        if index < 0: raise ValueError()
        page = row.pages[index]
    except (ValueError, IndexError):
        error(404, 'source_unavailable', 'This material source is unavailable.')
    return {'id': source_id, 'text': page['text'], 'label': row.name + ' · ' + page['label'],
        'source_kind': row.kind, 'sha256': row.sha256}


class Upload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=160)
    kind: Literal['syllabus', 'curriculum', 'slides']
    data: str = Field(min_length=1, max_length=11200000)
    expected_count: int = Field(ge=0)


def install_materials(app, current, db_session, owned_course, owned_lecture, receipt):
    def rows(db, course_id, lecture_id):
        return list(db.scalars(select(CourseMaterial).where(CourseMaterial.course_id == course_id,
            or_(CourseMaterial.lecture_id.is_(None), CourseMaterial.lecture_id == lecture_id)
            if lecture_id else CourseMaterial.lecture_id.is_(None)).order_by(CourseMaterial.created_at, CourseMaterial.id)))

    def summary(row):
        return {'id': row.id, 'name': row.name, 'kind': row.kind, 'pages': row.pages, 'sha256': row.sha256}

    def save(db, request, session, course_id, lecture_id, body):
        from .notes import latest, schedule_notes
        from .transcription import lock_lecture
        from .lifecycle import notify
        from .security import mutation
        mutation(request, session)
        owned_course(db, session.owner_id, course_id)
        if lecture_id: owned_lecture(db, session.owner_id, lecture_id)
        try:
            raw = base64.b64decode(body.data, validate=True)
            if len(raw) > MAX_BYTES or not raw: raise ValueError('size')
            pages = parse_upload(body.name, raw)
        except (ValueError, KeyError, UnicodeError, zipfile.BadZipFile, ET.ParseError, RuntimeError):
            error(422, 'material_unreadable', 'Use a readable PPTX, DOCX, PDF, UTF-8 TXT or Markdown file, up to 8 MiB, 300 pages/slides and 180,000 characters. Encrypted files, images and scanned text cannot be read. Export older PPT files as PPTX.')
        fingerprint_body = {'name': body.name, 'kind': body.kind, 'sha256': hashlib.sha256(raw).hexdigest(), 'expected_count': body.expected_count}
        # Serialize course additions and lecture creation on their common parent.
        db.scalar(select(Course).where(Course.id == course_id).with_for_update())
        action = 'materials:' + (lecture_id or course_id)
        previous, key, fingerprint = receipt(db, request, session, action, fingerprint_body)
        db.expire_all()
        owned_course(db, session.owner_id, course_id)
        if previous: return summary(db.get(CourseMaterial, previous.result_id))
        existing = rows(db, course_id, lecture_id)
        if len(existing) != body.expected_count:
            error(409, 'materials_changed', 'Materials changed in another window. Refresh the list and try again.')
        if len(existing) >= 20:
            error(422, 'material_limit', 'This workspace supports 20 materials per lecture or course.')
        lectures = list(db.scalars(select(Lecture).where(Lecture.course_id == course_id, Lecture.tombstoned.is_(False),
            Lecture.id == lecture_id if lecture_id else True).order_by(Lecture.id)))
        for lecture in lectures:
            lock_lecture(db, lecture.id)
            if lecture.tombstoned: error(404, 'unavailable', 'This lecture is unavailable.')
        row = CourseMaterial(course_id=course_id, lecture_id=lecture_id, name=body.name, kind=body.kind,
            sha256=fingerprint_body['sha256'], original=body.data, pages=pages)
        db.add(row); db.flush()
        for lecture in lectures:
            old = latest(db, SettingsVersion, lecture.id, SettingsVersion.version)
            fields = {k: getattr(old, k) for k in ('depth', 'format', 'instructions', 'detail_prompt', 'layout_prompt', 'ai_explanations')}
            db.add(SettingsVersion(lecture_id=lecture.id, version=old.version+1,
                material_ids=[*old.material_ids, row.id], **fields))
            db.execute(update(Job).where(Job.lecture_id == lecture.id, Job.kind == 'notes.generate',
                Job.status.in_(['due', 'running'])).values(status='cancelled', error_code='superseded'))
            db.flush()
            schedule_notes(db, lecture)
            notify(db, lecture, 'materials.changed', row.id)
        db.add(CommandReceipt(owner_id=session.owner_id, action=action, key=key, fingerprint=fingerprint, result_id=row.id))
        db.commit()
        return summary(row)

    @app.get('/courses/{course_id}/materials')
    def course_list(course_id: str, session=Depends(current), db=Depends(db_session)):
        owned_course(db, session.owner_id, course_id)
        return [summary(r) for r in rows(db, course_id, None)]

    @app.post('/courses/{course_id}/materials', status_code=201)
    def course_upload(course_id: str, body: Upload, request: Request, session=Depends(current), db=Depends(db_session)):
        return save(db, request, session, course_id, None, body)

    @app.get('/lectures/{lecture_id}/materials')
    def lecture_list(lecture_id: str, session=Depends(current), db=Depends(db_session)):
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        return [summary(r) for r in rows(db, lecture.course_id, lecture.id)]

    @app.post('/lectures/{lecture_id}/materials', status_code=201)
    def lecture_upload(lecture_id: str, body: Upload, request: Request, session=Depends(current), db=Depends(db_session)):
        lecture = owned_lecture(db, session.owner_id, lecture_id)
        return save(db, request, session, lecture.course_id, lecture_id, body)

    @app.get('/courses/{course_id}/materials/{material_id}/download')
    def download(course_id: str, material_id: str, session=Depends(current), db=Depends(db_session)):
        owned_course(db, session.owner_id, course_id)
        row = db.get(CourseMaterial, material_id)
        if not row or row.course_id != course_id: error(404, 'unavailable', 'This material is unavailable.')
        if row.lecture_id: owned_lecture(db, session.owner_id, row.lecture_id)
        return Response(base64.b64decode(row.original), media_type='application/octet-stream',
            headers={'Content-Disposition': 'attachment', 'Cache-Control': 'no-store'})
