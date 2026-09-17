"""Question generation through the already selected provider; no fallback."""
from .cloud_notes import is_cloud
from .note_provider import NoteFailure, CONTEXT, OUTPUT
from .note_contract import compact
from .question_contract import messages, SCHEMA, GRAMMAR, PROMPT, parse_questions
from .security import digest


def generate_questions(provider, evidence, preference, on_preview=None):
    request_messages = messages(evidence)
    if len(compact(request_messages).encode()) > 24000:
        raise NoteFailure('context_limit')
    installed, details = provider.verify(preference.model, preference.model_digest)
    if is_cloud(preference.model):
        name = preference.model.split('/')[0]
        if provider.bridge:
            raw, metrics = provider.bridge.generate(preference.model, preference.model_digest, request_messages, on_preview)
        elif name in ('chatgpt', 'claude-subscription'):
            from .subscription_notes import subscription_generate
            raw, metrics = subscription_generate(name, details, request_messages, provider.connections.directory, on_preview)
        else:
            raw, metrics = provider.api_generate(name, details, request_messages, on_preview)
    else:
        local = getattr(provider, 'local', provider)
        bound = sum(len(message['content'].encode()) for message in request_messages) + len(details.get('template', '').encode()) + 1024
        if bound + OUTPUT > CONTEXT:
            raise NoteFailure('context_limit')
        options = {'temperature': 0, 'seed': 42, 'num_ctx': CONTEXT, 'num_predict': OUTPUT}
        body = {'model': preference.model, 'messages': request_messages, 'format': GRAMMAR,
            'stream': False, 'think': False, 'keep_alive': '2m', 'options': options}
        probe = local.request('chat', {**body, 'options': {**options, 'num_predict': 1}}, timeout=600)
        tokens = probe.get('prompt_eval_count')
        if type(tokens) is not int or tokens <= 0 or tokens + OUTPUT + 512 > CONTEXT:
            raise NoteFailure('context_limit')
        provider.verify(preference.model, preference.model_digest)
        response = local.stream_chat(body, on_preview) if on_preview else local.request('chat', body, timeout=600)
        if response.get('done') is not True or response.get('done_reason') != 'stop':
            raise NoteFailure('truncated_output')
        if response.get('message', {}).get('tool_calls'):
            raise NoteFailure('invalid_output')
        raw = response.get('message', {}).get('content', '')
        metrics = {'preflight_prompt_tokens': tokens, 'eval_count': response.get('eval_count')}
    provider.verify(preference.model, preference.model_digest)
    try:
        content = parse_questions(raw, evidence)
    except (ValueError, KeyError, TypeError):
        raise NoteFailure('invalid_output') from None
    return content, {'model': preference.model, 'model_digest': installed['digest'],
        'processing_location': 'cloud' if is_cloud(preference.model) else 'local',
        'prompt_sha256': digest(PROMPT), 'schema_sha256': digest(compact(SCHEMA)),
        'provider_schema_sha256': digest(compact(GRAMMAR)),
        'input_sha256': digest(compact(evidence)), 'adapter_version': 'questions-v1',
        'metrics': metrics, 'semantic_support': 'not_evaluated', 'human_review': 'pending'}
