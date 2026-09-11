import copy
from uuid import uuid4
import pytest
from jsonschema import ValidationError
from test_workspace import setup
from test_capture import capture
from test_transcription import speech
from test_notes import notes, FakeNotes
from notetaker.note_draft import canonical, prepare
from notetaker.note_worker import plan, claim, execute
from notetaker.visual_notes import diagram_svg, html_notes


DIAGRAM = {'caption': 'ATP transfers energy',
    'nodes': [{'id': 'atp', 'label': 'ATP'}, {'id': 'adp', 'label': 'ADP + phosphate'}],
    'edges': [{'from': 'atp', 'to': 'adp', 'label': 'hydrolysis releases energy'}]}


def test_diagram_validated_and_escaped():
    evidence = {'source_snapshot_id':'snap', 'settings_version':1, 'allow_ai_explanations':False,
        'sources':[{'id':'source', 'text':'ATP hydrolysis yields ADP and phosphate, releasing energy.'}]}
    _, citations = prepare(evidence)
    draft = {'blocks':[{'topic':'Energy', 'kind':'explanation', 'diagram':copy.deepcopy(DIAGRAM),
        'passages':[{'text':'ATP transfers energy.', 'source_ids':['s1']}]}], 'issues':[]}
    output = canonical(draft, evidence, citations)
    assert output['blocks'][0]['diagram'] == DIAGRAM
    for invalid in ('missing', 'atp'):
        draft['blocks'][0]['diagram']['edges'][0]['to'] = invalid
        with pytest.raises(ValueError): canonical(draft, evidence, citations)
    draft['blocks'][0]['diagram'] = copy.deepcopy(DIAGRAM)
    draft['blocks'][0]['diagram']['nodes'][1]['id'] = 'atp'
    with pytest.raises(ValueError): canonical(draft, evidence, citations)
    draft['blocks'][0]['diagram'] = {**DIAGRAM, 'html':'<script>alert(1)</script>'}
    with pytest.raises(ValidationError): canonical(draft, evidence, citations)
    malicious = copy.deepcopy(DIAGRAM)
    malicious['nodes'][0]['label'] = '</text><script>attack</script>'
    svg = diagram_svg(malicious)
    assert '<script>' not in svg and '&lt;' in svg
    result = html_notes('<img src=x>', output, '<script>source appendix</script>')
    assert '<img' not in result and '<script>' not in result
    assert "default-src 'none'" in result and '<svg' in result


class VisualProvider(FakeNotes):
    def generate(self, evidence, pref):
        result, metadata = super().generate(evidence, pref)
        result['blocks'][0]['diagram'] = copy.deepcopy(DIAGRAM)
        return result, metadata


def test_visual_revision_edit_export_undo_and_ownership(notes):
    app, client, headers, path, _ = notes
    plan(app.state.sessions)
    assert execute(app.state.sessions, VisualProvider(), claim(app.state.sessions), heartbeat=False)
    revision = client.get(path+'/notes').json()['revision']
    endpoint = path+'/notes/revisions/'+revision['id']+'/export?format=html'
    original = client.get(endpoint)
    assert original.status_code == 200 and '<svg' in original.text and 'Source appendix' in original.text
    body = {'expected_version':0, 'action':'save', 'base_id':revision['id'],
        'passages':[{'id':revision['content']['blocks'][0]['passages'][0]['id'], 'text':'My <script> correction'}]}
    edited = client.post(path+'/notes/edits', json=body, headers={**headers, 'idempotency-key':str(uuid4())}).json()
    saved = client.get(path+'/notes/edits/'+edited['id']+'/export?format=html')
    assert 'Review diagram:' in saved.text and 'My &lt;script&gt; correction' in saved.text
    assert '<script>' not in saved.text and client.get(endpoint).text == original.text
    other = client.get('/lectures/other/notes/revisions/'+revision['id']+'/export?format=html')
    assert other.status_code == 404
    undo = client.post(path+'/notes/edits', json={'expected_version':1, 'action':'undo',
        'base_id':edited['id'], 'target_id':revision['id']}, headers={**headers, 'idempotency-key':str(uuid4())})
    assert undo.status_code == 200 and undo.json()['content']['blocks'][0]['diagram'] == DIAGRAM
