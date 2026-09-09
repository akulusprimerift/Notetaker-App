import base64
import io
import zipfile
from uuid import uuid4
import pytest
from sqlalchemy import select
from test_notes import notes, speech, FakeNotes
from test_capture import capture
from test_workspace import setup
from test_note_edits import saved_edit, command
from notetaker.materials import extract
from notetaker.models import CourseMaterial, Lecture, SettingsVersion
from notetaker.note_worker import claim, execute


def upload(client, headers, path, text='Binary search requires sorted input.', count=0, key=None):
    return client.post(path+'/materials', headers={**headers, 'idempotency-key': key or str(uuid4())},
        json={'name': 'Syllabus.txt', 'kind': 'syllabus', 'data': base64.b64encode(text.encode()).decode(), 'expected_count': count})


def test_material_regeneration_protects_edits_and_sources(notes):
    app, client, headers, path, _ = notes
    original, edited, _ = saved_edit(notes)
    export = client.get(path+'/notes/revisions/'+original['id']+'/export').text
    key = str(uuid4())
    response = upload(client, headers, path, key=key)
    assert response.status_code == 201, response.text
    assert upload(client, headers, path, key=key).json()['id'] == response.json()['id']
    assert upload(client, headers, path).status_code == 409
    assert execute(app.state.sessions, FakeNotes(), claim(app.state.sessions), heartbeat=False)
    state = client.get(path+'/notes').json()
    assert state['editing']['selected']['id'] == edited['id']
    assert state['editing']['proposal_valid']
    proposal = state['editing']['proposal']
    source_id = next(c['source_id'] for c in proposal['content']['coverage'] if c['source_id'].startswith('material:'))
    source = client.get(path+'/sources/'+source_id).json()
    assert source['label'] == 'Syllabus.txt · Document'
    assert 'audio_url' not in source
    assert client.get(path+'/notes/revisions/'+original['id']+'/export').text == export
    assert 'Uploaded material' in client.get(path+'/notes/revisions/'+proposal['id']+'/export').text
    replaced = command(client, headers, path, {'expected_version': edited['revision'], 'base_id': edited['id'],
        'action': 'replace', 'proposal_id': proposal['id']})
    assert replaced.status_code == 200, replaced.text
    assert any(c['source_id'] == source_id for c in replaced.json()['resolved_citations'])


def test_upload_fences_running_attempt_and_course_applies_to_new_lectures(notes):
    app, client, headers, path, _ = notes
    with app.state.sessions() as db:
        course = db.get(Lecture, path.split('/')[-1]).course_id
    def changed():
        assert upload(client, headers, '/courses/'+course).status_code == 201
    assert not execute(app.state.sessions, FakeNotes(after=changed), claim(app.state.sessions), heartbeat=False)
    response = client.post('/courses/'+course+'/lectures', headers={**headers, 'idempotency-key': str(uuid4())}, json={'title': 'Next lecture'})
    assert response.status_code == 201
    with app.state.sessions() as db:
        settings = db.scalar(select(SettingsVersion).where(SettingsVersion.lecture_id == response.json()['id']))
        assert len(settings.material_ids) == 1
    assert len(client.get('/lectures/'+response.json()['id']+'/materials').json()) == 1


def test_material_authority_and_tombstone(notes):
    app, client, headers, path, _ = notes
    assert upload(client, {}, path).status_code == 403
    assert upload(client, headers, path, text='').status_code == 422
    assert upload(client, headers, path).status_code == 201
    with app.state.sessions() as db:
        lecture = db.get(Lecture, path.split('/')[-1]); lecture.tombstoned = True
        from notetaker.lifecycle import erase_content
        erase_content(db, lecture); db.commit()
        assert db.scalar(select(CourseMaterial)) is None
    assert client.get(path+'/materials').status_code == 404
    assert upload(client, headers, path, count=1).status_code == 404


def test_pptx_text_and_archive_failures():
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="urn:p" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldId r:id="a"/><p:sldId r:id="b"/></p:presentation>')
        archive.writestr('ppt/_rels/presentation.xml.rels', '<Relationships><Relationship Id="a" Target="slides/slide1.xml"/><Relationship Id="b" Target="slides/slide2.xml"/></Relationships>')
        archive.writestr('ppt/slides/slide2.xml', '<s xmlns:a="urn:a"><a:p><a:r><a:t>Second</a:t></a:r></a:p></s>')
        archive.writestr('ppt/slides/slide1.xml', '<s xmlns:a="urn:a"><a:p><a:r><a:t>First</a:t></a:r></a:p></s>')
    assert [p['text'] for p in extract('slides.pptx', data.getvalue())] == ['First', 'Second']
    with pytest.raises(ValueError): extract('old.ppt', b'legacy')
    with pytest.raises(ValueError): extract('empty.txt', b' ')
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('word/document.xml', '<!DOCTYPE a><a/>')
    with pytest.raises(ValueError): extract('unsafe.docx', data.getvalue())


def test_pdf_syllabus_and_blank_scan_are_distinguished():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    from notetaker.materials import parse_upload
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 72 720 Td (Course syllabus: binary search) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    data = io.BytesIO(); writer.write(data)
    assert 'Course syllabus' in parse_upload('syllabus.pdf', data.getvalue())[0]['text']
    blank = PdfWriter(); blank.add_blank_page(width=612, height=792)
    data = io.BytesIO(); blank.write(data)
    with pytest.raises(ValueError): parse_upload('scan.pdf', data.getvalue())


def test_large_mixed_batches_pair_transcript_and_material_evidence():
    from types import SimpleNamespace
    from test_notes import DIGEST
    from notetaker.note_batches import generate_batches, BATCH_BYTES
    evidence = {'source_snapshot_id': 'test', 'settings_version': 1, 'allow_ai_explanations': False,
        'profile': {'depth': 'detailed', 'format': 'topic_outline'},
        'sources': [{'id': 'speech', 'text': 'Binary search requires sorted input.'},
            *[{'id': f'material:{i}', 'source_kind': 'slides', 'text': 'Binary search details. '*100} for i in range(8)]]}
    class Paired(FakeNotes):
        def generate(self, part, pref):
            assert sum(len(s['text'].encode()) for s in part['sources']) <= BATCH_BYTES
            assert any(s.get('source_kind') for s in part['sources'])
            assert any(not s.get('source_kind') for s in part['sources'])
            return super().generate(part, pref)
    content, metadata = generate_batches(Paired(), evidence, SimpleNamespace(model='qwen3:4b', model_digest=DIGEST))
    assert len(content['coverage']) == 9
    assert metadata['batch_count'] > 1
