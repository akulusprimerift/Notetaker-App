"""Canonical Phase 4 contract, enforced independently of provider generation grammar."""
import json
import sys
from copy import deepcopy
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[3]))
SCHEMA = json.loads((ROOT / 'contracts/ai/note-output-materials.schema.json').read_text(encoding='utf-8'))
PROMPT = (ROOT / 'prompts/note-generation-v3.txt').read_text(encoding='utf-8')
VALIDATOR = Draft202012Validator(SCHEMA)
AGGREGATE_SCHEMA = deepcopy(SCHEMA)
for key, maximum in (('blocks', 10000), ('issues', 10000), ('coverage', 20000)):
    AGGREGATE_SCHEMA['properties'][key]['maxItems'] = maximum
AGGREGATE_VALIDATOR = Draft202012Validator(AGGREGATE_SCHEMA)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def grammar(node):
    if isinstance(node, list): return [grammar(item) for item in node]
    if not isinstance(node, dict): return node
    if '$ref' in node: return grammar(SCHEMA['$defs'][node['$ref'].removeprefix('#/$defs/')])
    omit = {'$schema', '$id', '$defs', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minimum', 'maximum', 'uniqueItems'}
    return {key: grammar(value) for key, value in node.items() if key not in omit}


GRAMMAR = grammar(SCHEMA)


def messages(evidence):
    return [{'role': 'system', 'content': PROMPT + '\nOUTPUT_SCHEMA:\n' + compact(SCHEMA)},
        {'role': 'user', 'content': 'LECTURE_EVIDENCE_JSON:\n' + compact(evidence)}]


def validate_notes(output, evidence, aggregate=False):
    # Never return validator exceptions or model text in HTTP errors or logs.
    (AGGREGATE_VALIDATOR if aggregate else VALIDATOR).validate(output)
    if output['source_snapshot_id'] != evidence['source_snapshot_id'] or output['settings_version'] != evidence['settings_version']:
        raise ValueError('stale_metadata')
    sources = {s['id']: s for s in evidence['sources']}
    blocks, passages, cited, resolved = set(), set(), set(), []
    for block in output['blocks']:
        if 'diagram' in block:
            from .visual_notes import validate_diagram
            validate_diagram(block['diagram'])
            if not any(p['sources'] for p in block['passages']):
                raise ValueError('diagram_evidence_required')
        if block['id'] in blocks: raise ValueError('duplicate_block')
        blocks.add(block['id'])
        for passage in block['passages']:
            if passage['id'] in passages or not passage['text'].strip(): raise ValueError('invalid_passage')
            passages.add(passage['id'])
            kind = passage['evidence_kind']
            if kind in ('lecture_paraphrase', 'material_paraphrase', 'exact_quote') and not passage['sources']: raise ValueError('evidence_required')
            if kind == 'ai_explanation' and (not evidence['allow_ai_explanations'] or passage['sources']): raise ValueError('explanation_disabled')
            for citation in passage['sources']:
                if citation['source_id'] not in sources: raise ValueError('unknown_source')
                source = sources[citation['source_id']]
                offset = -1
                # Bound adversarial occurrence before looping. Python indices are Unicode code points.
                if citation['occurrence'] > len(source['text']): raise ValueError('invalid_occurrence')
                for _ in range(citation['occurrence'] + 1):
                    offset = source['text'].find(citation['quote'], offset + 1)
                    if offset < 0: raise ValueError('quote_missing')
                cited.add(source['id'])
                resolved.append({'passage_id': passage['id'], 'source_id': source['id'],
                    'start': offset, 'end': offset + len(citation['quote'])})
            if kind == 'exact_quote' and (len(passage['sources']) != 1 or passage['text'] != passage['sources'][0]['quote']):
                raise ValueError('not_verbatim')
    covered = set()
    for item in output['coverage']:
        source = item['source_id']
        if source not in sources or source in covered or not item['reason'].strip(): raise ValueError('invalid_coverage')
        if (item['disposition'] == 'used') != (source in cited): raise ValueError('coverage_mismatch')
        covered.add(source)
    if covered != sources.keys(): raise ValueError('missing_coverage')
    for issue in output['issues']:
        if any(s not in sources for s in issue['source_ids']): raise ValueError('unknown_issue_source')
        if issue['code'] != 'incomplete_evidence' and not issue['source_ids']: raise ValueError('issue_source_required')
    if not sources and output['blocks']: raise ValueError('invented_notes')
    if not output['blocks'] and not output['issues']: raise ValueError('empty_notes')
    return resolved
