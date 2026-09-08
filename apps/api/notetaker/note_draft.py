"""Convert model-written prose to canonical notes using server-owned source identity."""
import json
from jsonschema import Draft202012Validator
from .note_contract import ROOT, SCHEMA, compact, validate_notes

DRAFT_SCHEMA = json.loads((ROOT/'contracts/ai/note-draft.schema.json').read_text(encoding='utf-8'))
DRAFT_PROMPT = (ROOT/'prompts/note-draft-v1.txt').read_text(encoding='utf-8')


def grammar(node):
    if isinstance(node, list): return [grammar(item) for item in node]
    if not isinstance(node, dict): return node
    return {key: grammar(value) for key, value in node.items()
        if key not in {'$schema', 'minLength', 'maxLength', 'minItems', 'maxItems', 'uniqueItems'}}


DRAFT_GRAMMAR = grammar(DRAFT_SCHEMA)


def prepare(evidence):
    sources, citations = [], {}
    for original in evidence['sources']:
        text = original['text']; start = 0
        while start < len(text):
            end = min(start + 3000, len(text))
            if end < len(text):
                boundary = text.rfind(' ', start + 2000, end)
                if boundary > start: end = boundary
            excerpt = text[start:end]
            alias = 's' + str(len(sources) + 1)
            occurrence, found = 0, text.find(excerpt)
            while found < start:
                found = text.find(excerpt, found + 1); occurrence += 1
            citations[alias] = {'source_id': original['id'], 'quote': excerpt, 'occurrence': occurrence}
            sources.append({'id': alias, 'text': excerpt})
            start = end
    request = {'profile': evidence.get('profile', {'depth': 'detailed', 'format': 'topic_outline'}), 'sources': sources}
    return request, citations


def draft_messages(request):
    profile = request['profile']
    depth = {'detailed': 'Write detailed study notes, including definitions, explanations, worked steps, examples and conditions that the sources support.',
        'standard': 'Write standard study notes: concise explanations with the important examples and conditions.',
        'brief': 'Write brief revision notes. Each passage must be only one or two short sentences. Retain essential conditions and corrections.'}[profile['depth']]
    layout = {'topic_outline': 'Organize the notes under descriptive topic headings.',
        'cornell': 'Use Cornell notes: each topic must be a concise study question ending in a question mark; its passages answer that cue.',
        'question_answer': 'Use a question-and-answer study guide: EVERY topic must be a direct question ending in a question mark, and each passage must answer that question.'}[profile['format']]
    return [{'role': 'system', 'content': DRAFT_PROMPT + '\nJSON_SCHEMA:\n' + compact(DRAFT_SCHEMA)},
        {'role': 'user', 'content': 'LECTURE TRANSCRIPT:\n' + compact(request['sources']) +
            '\n\nWRITE THE NOTES NOW. ' + depth + ' ' + layout +
            '\nStudent writing preferences: ' + profile.get('instructions', '') +
            '\nUse your own explanatory wording. Do not simply copy the transcript sentences. Return only the JSON notes.'}]


def canonical(draft, evidence, citations):
    Draft202012Validator(DRAFT_SCHEMA).validate(draft)
    def refs(ids):
        if any(source not in citations for source in ids): raise ValueError('unknown_source')
        return [dict(citations[source]) for source in ids]
    blocks, cited = [], set()
    for index, block in enumerate(draft['blocks']):
        passages = []
        for number, passage in enumerate(block['passages']):
            references = refs(passage['source_ids'])
            cited.update(c['source_id'] for c in references)
            passages.append({'id': f'b{index+1}p{number+1}', 'text': passage['text'],
                'evidence_kind': 'uncertainty' if block['kind'] == 'uncertainty' else 'lecture_paraphrase', 'sources': references})
        blocks.append({'id': f'b{index+1}', 'topic': block['topic'], 'kind': block['kind'], 'passages': passages})
    issues = [{**issue, 'source_ids': list(dict.fromkeys(c['source_id'] for c in refs(issue['source_ids'])))} for issue in draft['issues']]
    coverage = [{'source_id': source['id'], 'disposition': 'used' if source['id'] in cited else 'omitted',
        'reason': 'Referenced by these notes.' if source['id'] in cited else 'This generated draft did not use this passage; review the source for missing detail.'}
        for source in evidence['sources']]
    output = {'schema_version': 1, 'source_snapshot_id': evidence['source_snapshot_id'],
        'settings_version': evidence['settings_version'], 'blocks': blocks, 'issues': issues, 'coverage': coverage}
    validate_notes(output, evidence)
    return output
