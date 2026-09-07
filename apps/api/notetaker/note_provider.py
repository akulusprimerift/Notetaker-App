"""Local Ollama adapter. No downloads, tools, redirects, or remote fallback."""
import json
import re
import httpx
from .note_contract import compact, messages, GRAMMAR, SCHEMA, PROMPT
from .security import digest

CONTEXT = 32768
OUTPUT = 6000


def alias_evidence(evidence):
    # Short request-local labels identify immutable versions through a server-owned map.
    # This avoids asking a small model to repeatedly reproduce opaque UUIDs.
    aliases = {f's{i+1}': source['id'] for i, source in enumerate(evidence['sources'])}
    sources = [{**source, 'id': alias} for alias, source in zip(aliases, evidence['sources'])]
    return {**evidence, 'sources': sources}, aliases


def expand_sources(output, aliases):
    def resolve(source):
        if source not in aliases: raise NoteFailure('invalid_output')
        return aliases[source]
    try:
        for block in output['blocks']:
            for passage in block['passages']:
                for citation in passage['sources']: citation['source_id'] = resolve(citation['source_id'])
        for issue in output['issues']: issue['source_ids'] = [resolve(source) for source in issue['source_ids']]
        for entry in output['coverage']: entry['source_id'] = resolve(entry['source_id'])
    except (KeyError, TypeError): raise NoteFailure('invalid_output') from None
    return output


class NoteFailure(Exception):
    def __init__(self, code): self.code = code


class OllamaNotes:
    def __init__(self, settings): self.url = settings.ollama_url

    def request(self, route, body=None, timeout=10):
        try:
            with httpx.Client(base_url=self.url, timeout=timeout, trust_env=False, follow_redirects=False) as client:
                with client.stream('POST' if body is not None else 'GET', '/api/' + route, json=body) as response:
                    response.raise_for_status()
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 2_000_000: raise NoteFailure('invalid_output')
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get('error'): raise NoteFailure('model_unavailable')
            return data
        except (httpx.HTTPError, ValueError): raise NoteFailure('model_unavailable') from None

    def models(self):
        return [{'name': m['name'], 'digest': m['digest'], 'size': m['size'], 'family': m['details']['family']}
            for m in self.request('tags').get('models', [])
            if not m.get('remote_host') and not m.get('remote_model') and m.get('size', 0) > 1_000_000
            and m.get('details', {}).get('format') == 'gguf'
            and m.get('details', {}).get('family') in ('qwen2', 'qwen3')
            and re.fullmatch(r'[a-f0-9]{64}', m.get('digest', ''))
            and 0 < len(m.get('name', '')) <= 160 and 'cloud' not in m['name'].lower()]

    def verify(self, model, expected=None):
        installed = next((m for m in self.models() if m['name'] == model), None)
        if not installed: raise NoteFailure('model_unavailable')
        if expected and installed['digest'] != expected: raise NoteFailure('model_changed')
        details = self.request('show', {'model': model})
        if details.get('remote_host') or details.get('remote_model') or 'completion' not in details.get('capabilities', []):
            raise NoteFailure('model_unavailable')
        info = details.get('model_info', {})
        if max((v for k, v in info.items() if k.endswith('.context_length') and isinstance(v, int)), default=0) < CONTEXT:
            raise NoteFailure('model_context_unsupported')
        return installed, details

    def generate(self, evidence, preference):
        installed, details = self.verify(preference.model, preference.model_digest)
        request_evidence, aliases = alias_evidence(evidence)
        request_messages = messages(request_evidence)
        # Qwen byte-level BPE cannot produce more ordinary tokens than input UTF-8 bytes.
        # Include the entire template plus a 1024-token reserve for special tokens. Do not
        # apply this guard to other tokenizers. Reject whole input rather than truncate it.
        bound = sum(len(m['content'].encode()) for m in request_messages) + len(details.get('template', '').encode()) + 1024
        if bound + OUTPUT > CONTEXT or len(evidence['sources']) > 200:
            raise NoteFailure('context_limit')
        options = {'temperature': 0, 'seed': 42, 'num_ctx': CONTEXT, 'num_predict': OUTPUT}
        body = {'model': preference.model, 'messages': request_messages, 'format': GRAMMAR,
            'stream': False, 'think': False, 'keep_alive': '2m', 'options': options}
        # Ask this model to evaluate the identical prompt with one throwaway output token.
        # This gives an actual tokenizer count before the note-generation request.
        probe = self.request('chat', {**body, 'options': {**options, 'num_predict': 1}}, timeout=600)
        tokens = probe.get('prompt_eval_count')
        if type(tokens) is not int or tokens <= 0 or tokens + OUTPUT + 512 > CONTEXT:
            raise NoteFailure('context_limit')
        self.verify(preference.model, preference.model_digest)
        response = self.request('chat', body, timeout=600)
        self.verify(preference.model, preference.model_digest)
        if response.get('done') is not True or response.get('done_reason') != 'stop': raise NoteFailure('truncated_output')
        if response.get('message', {}).get('tool_calls'): raise NoteFailure('invalid_output')
        try: output = json.loads(response['message']['content'])
        except (KeyError, TypeError, ValueError): raise NoteFailure('invalid_output') from None
        return expand_sources(output, aliases), {'provider': 'ollama_local', 'model': preference.model, 'model_digest': installed['digest'],
            'ollama_version': self.request('version').get('version'), 'prompt_version': 'v3',
            'prompt_sha256': digest(PROMPT), 'schema_sha256': digest(compact(SCHEMA)),
            'provider_schema_sha256': digest(compact(GRAMMAR)), 'input_sha256': digest(compact(evidence)),
            'source_aliases': aliases, 'request_sha256': digest(compact(request_evidence)),
            'options': options, 'preflight_prompt_tokens': tokens, 'prompt_byte_upper_bound': bound,
            'metrics': {k: response.get(k) for k in ('prompt_eval_count', 'eval_count', 'total_duration')},
            'semantic_support': 'not_evaluated', 'human_review': 'pending'}
