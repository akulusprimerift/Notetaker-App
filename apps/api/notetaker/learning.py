"""Build source-checked context from the currently selected saved notes."""
from hashlib import sha256
from fastapi import HTTPException
from . import models as m
from .materials import source_for_lecture
from .note_edits import head
from .notes import latest
from .transcription import snapshot_json


def saved_note_context(db, lecture):
    selected = head(db, lecture.id) or latest(db, m.NoteRevision, lecture.id, m.NoteRevision.revision)
    result = {'revision_id': selected.id if selected else None, 'blocks': [], 'omitted': 0, 'issues': []}
    if not selected:
        return result
    snapshot = latest(db, m.TranscriptSnapshot, lecture.id, m.TranscriptSnapshot.sequence)
    sources = {s['id']: s for s in snapshot_json(db, snapshot)['segments']} if snapshot else {}
    result['issues'] = selected.content['issues'] + (snapshot.issues if snapshot else [])
    for block in selected.content['blocks']:
        # Keep complete blocks: silently dropping an unsupported qualifier can change an answer.
        passages = block['passages']
        ids = set()
        note_sources = []
        context_passages = []
        eligible = bool(passages)
        for passage in passages:
            citations = passage['sources']
            student_authored = passage['evidence_kind'] == 'student_note' or bool(passage.get('student_edited'))
            if not citations and student_authored:
                # Personal note text is evidence of the selected student revision, not a claim
                # that the lecturer said it. Keep the full text in sources and pin its identity.
                suffix = sha256(passage['id'].encode('utf-8')).hexdigest()
                source_id = f'note-revision:{selected.id}:{suffix}'
                note_sources.append({'id': source_id, 'text': passage['text'],
                    'label': 'Student note · ' + block['topic'], 'source_kind': 'student_note',
                    'revision_id': selected.id, 'passage_id': passage['id']})
                context_passages.append({'id': passage['id'], 'student_edited': True,
                    'evidence_kind': 'student_note', 'note_source_id': source_id})
                continue
            if not citations or (passage['evidence_kind'] not in (
                    'exact_quote', 'lecture_paraphrase', 'material_paraphrase') and not student_authored):
                eligible = False
            ids.update(citation['source_id'] for citation in citations)
            context_passages.append({'id': passage['id'], 'text': passage['text'],
                'student_edited': bool(passage.get('student_edited')),
                'evidence_kind': passage['evidence_kind'], 'sources': citations})
        for ident in ids:
            if ident.startswith('material:'):
                try:
                    sources[ident] = source_for_lecture(db, lecture, ident)
                except (HTTPException, ValueError):
                    eligible = False
            elif ident not in sources:
                eligible = False
        # A visual exercise cannot be represented faithfully by a text-only card.
        if not eligible or 'diagram' in block:
            result['omitted'] += 1
            continue
        result['blocks'].append({'id': block['id'], 'topic': block['topic'],
            'passages': context_passages,
            'sources': [sources[ident] for ident in sorted(ids)] + note_sources})
    return result
