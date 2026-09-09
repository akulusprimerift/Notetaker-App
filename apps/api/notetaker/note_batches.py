"""Bound each model call, reuse unchanged source-backed notes, retain all coverage."""
from copy import deepcopy
import re
from .note_contract import validate_notes

BATCH_BYTES = 8000
BATCH_SOURCES = 16


def reusable(previous, evidence):
    if not previous or previous['profile'] != evidence['profile']:
        return False
    old = {s['source_id'] for s in previous['content']['coverage']}
    return old <= {s['id'] for s in evidence['sources']}


def generate_batches(provider, evidence, preference, previous=None, on_preview=None):
    reuse = reusable(previous, evidence)
    content = deepcopy(previous['content']) if reuse else {
        'schema_version': 1, 'blocks': [], 'issues': [], 'coverage': []}
    content.update(source_snapshot_id=evidence['source_snapshot_id'], settings_version=evidence['settings_version'])
    done = {s['source_id'] for s in content['coverage']}
    pending = [s for s in evidence['sources'] if s['id'] not in done]
    has_materials = any(s.get('source_kind') for s in evidence['sources'])
    # Leave room to pair each passage batch with relevant evidence of the other kind.
    target_bytes = 5000 if has_materials else BATCH_BYTES
    batches, batch, size = [], [], 0
    for source in pending:
        cost = len(source['text'].encode('utf-8'))
        if batch and (size + cost > target_bytes or len(batch) >= BATCH_SOURCES):
            batches.append(batch); batch, size = [], 0
        batch.append(source); size += cost
    if batch:
        batches.append(batch)
    metadata = deepcopy(previous['metadata']) if reuse else {}
    batch_records = deepcopy(metadata.get('batches', []))
    completed_text = ''
    for batch in batches:
        if has_materials:
            material_batch = all(s.get('source_kind') for s in batch)
            terms = set(re.findall(r'\w{4,}', ' '.join(s['text'] for s in batch).lower()))
            candidates = [s for s in evidence['sources'] if bool(s.get('source_kind')) != material_batch and s not in batch]
            candidates.sort(key=lambda s: len(terms & set(re.findall(r'\w{4,}', s['text'].lower()))), reverse=True)
            budget = BATCH_BYTES - sum(len(s['text'].encode('utf-8')) for s in batch)
            for source in candidates:
                cost = len(source['text'].encode('utf-8'))
                if cost <= budget and len(batch) < BATCH_SOURCES:
                    batch = [*batch, source]
                    break
        first = next(i for i, s in enumerate(evidence['sources']) if s['id'] == batch[0]['id'])
        # Context helps continuity but is not a newly covered or citeable source.
        context = '\n'.join(s['text'] for s in evidence['sources'][max(0, first-2):first])[-2500:]
        part = {**evidence, 'sources': batch, 'preceding_context': context}
        if on_preview and hasattr(provider, 'generate_stream'):
            output, metadata = provider.generate_stream(part, preference,
                lambda value: on_preview(completed_text + value))
        else:
            output, metadata = provider.generate(part, preference)
        validate_notes(output, part)
        if metadata.get('model') != preference.model or metadata.get('model_digest') != preference.model_digest:
            raise ValueError('model_identity')
        batch_records.append({'source_ids': [s['id'] for s in batch], 'details': metadata})
        for block in output['blocks']:
            block = deepcopy(block)
            block['id'] = f"b{len(content['blocks'])+1}"
            for index, passage in enumerate(block['passages']):
                passage['id'] = f"{block['id']}p{index+1}"
            content['blocks'].append(block)
            completed_text += block['topic'] + '\n' + '\n'.join(p['text'] for p in block['passages']) + '\n\n'
        content['issues'].extend(output['issues'])
        coverage = {c['source_id']: c for c in content['coverage']}
        for entry in output['coverage']:
            prior = coverage.get(entry['source_id'])
            if not prior or prior['disposition'] != 'used':
                coverage[entry['source_id']] = entry
        content['coverage'] = list(coverage.values())
        if on_preview:
            on_preview(completed_text)
    validate_notes(content, evidence, aggregate=True)
    metadata = {**metadata, 'batch_count': len(batches), 'reused_sources': len(done),
        'input_source_count': len(evidence['sources']), 'batches': batch_records}
    return content, metadata
