"""Exercise the service command used by installed-app uploads with real bytes."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest


def document(extension):
    if extension in ('.txt', '.md'):
        return 'Course syllabus: café\nLecture requirements'.encode('utf-8')
    data = io.BytesIO()
    if extension == '.pdf':
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 72 720 Td (Course syllabus) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        writer.write(data)
    else:
        with zipfile.ZipFile(data, 'w') as archive:
            if extension == '.pptx':
                archive.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="urn:p" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<p:sldId r:id="a"/></p:presentation>')
                archive.writestr('ppt/_rels/presentation.xml.rels', '<Relationships>'
                    '<Relationship Id="a" Target="slides/slide1.xml"/></Relationships>')
                name = 'ppt/slides/slide1.xml'
            else:
                name = 'word/document.xml'
            archive.writestr(name, '<d xmlns:a="urn:a"><a:p><a:r><a:t>Course syllabus</a:t>'
                '</a:r></a:p></d>')
    return data.getvalue()


@pytest.fixture
def service_command():
    # Set this to also run the same regression against an actual frozen build.
    executable = os.environ.get('NOTETAKER_TEST_SERVICE_EXECUTABLE')
    if executable:
        return [executable]
    return [sys.executable, str(Path(__file__).resolve().parents[1] / 'windows_service.py')]


@pytest.mark.parametrize('extension', ['.pptx', '.docx', '.pdf', '.txt', '.md'])
def test_service_extracts_supported_uploads(service_command, extension, monkeypatch):
    result = subprocess.run([*service_command, 'material-parser', extension],
        input=document(extension), capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    assert 'Course syllabus' in json.loads(result.stdout)[0]['text']
    if os.environ.get('NOTETAKER_TEST_SERVICE_EXECUTABLE'):
        from notetaker import materials
        monkeypatch.setattr(materials, 'sys', SimpleNamespace(frozen=True,
            executable=service_command[0], platform=sys.platform))
        assert materials.parse_upload('syllabus'+extension, document(extension)) == json.loads(result.stdout)


@pytest.mark.parametrize(('extension', 'raw'), [('.pdf', b'not a PDF'), ('.pptx', b'broken ZIP'),
    ('.txt', b' '), ('.txt', b'\xff'), ('.ppt', b'unsupported')])
def test_service_rejects_unreadable_uploads_without_echoing_content(service_command, extension, raw):
    result = subprocess.run([*service_command, 'material-parser', extension],
        input=raw, capture_output=True, timeout=20, check=False)
    assert result.returncode == 1
    assert result.stdout == b''
    assert raw not in result.stderr
