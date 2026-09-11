"""User-selected cloud adapters, using the same source validation and revision fencing."""
import json
import httpx
from .note_provider import OllamaNotes, NoteFailure, preview_text
from .note_draft import prepare, draft_messages, canonical, DRAFT_SCHEMA, DRAFT_PROMPT
from .note_contract import compact
from .provider_connections import Connections, PROVIDERS
from .provider_bridge import ProviderBridge, ProviderBridgeError
from .security import digest


def is_cloud(model):
    return model.partition('/')[0] in PROVIDERS


class NoteProviders:
    def __init__(self, settings, transport=None):
        self.local = OllamaNotes(settings)
        bridge_url = getattr(settings, 'provider_bridge_url', '')
        self.bridge = ProviderBridge(bridge_url, getattr(settings, 'provider_bridge_token', '')) if bridge_url else None
        self.connections = Connections(settings.provider_directory if settings.standalone else '')
        self.transport = transport

    def inventory(self):
        return self.bridge.inventory() if self.bridge else self.connections.inventory()

    def models(self):
        try:
            local = self.local.models()
        except NoteFailure:
            local = []
        return local + self.inventory()

    def model_inventory(self):
        try:
            local = self.local.models()
            available = True
        except NoteFailure:
            local, available = [], False
        try:
            connections = self.inventory()
        except NoteFailure:
            connections = []
        return local + connections, available

    def verify(self, model, expected=None):
        if not is_cloud(model):
            return self.local.verify(model, expected)
        if self.bridge:
            return self.bridge.verify(model, expected)
        try:
            provider, name = model.split('/', 1)
            row = self.connections.read(provider)
            if not row or row['model'] != name or (expected and row['id'] != expected):
                raise ValueError('connection_changed')
            return {'name':model, 'digest':row['id']}, row
        except (OSError, ValueError, KeyError):
            raise NoteFailure('connection_unavailable') from None

    def generate_stream(self, evidence, preference, on_preview):
        return self.generate(evidence, preference, on_preview)

    def generate(self, evidence, preference, on_preview=None):
        if not is_cloud(preference.model):
            return self.local.generate(evidence, preference, on_preview)
        installed, row = self.verify(preference.model, preference.model_digest)
        provider = preference.model.split('/')[0]
        request, citations = prepare(evidence)
        messages = draft_messages(request)
        if len(compact(messages).encode()) > 100000:
            raise NoteFailure('context_limit')
        if self.bridge:
            raw, metrics = self.bridge.generate(preference.model, preference.model_digest, messages, on_preview)
        elif provider in ('chatgpt', 'claude-subscription'):
            from .subscription_notes import subscription_generate
            raw, metrics = subscription_generate(provider, row, messages, self.connections.directory, on_preview)
        else:
            raw, metrics = self.api_generate(provider, row, messages, on_preview)
        self.verify(preference.model, preference.model_digest)
        try:
            output = canonical(json.loads(raw), evidence, citations)
        except (ValueError, KeyError, TypeError):
            raise NoteFailure('invalid_output') from None
        return output, {'model':preference.model, 'model_digest':installed['digest'], 'provider':provider,
            'processing_location':'cloud', 'prompt_sha256':digest(DRAFT_PROMPT),
            'input_sha256':digest(compact(evidence)), 'provider_schema_sha256':digest(compact(DRAFT_SCHEMA)),
            'adapter_version':'cloud-draft-v1', 'metrics':metrics,
            'semantic_support':'not_evaluated', 'human_review':'pending'}

    def api_generate(self, provider, row, messages, on_preview):
        if provider == 'openai':
            url = 'https://api.openai.com/v1/chat/completions'
            headers = {'Authorization':'Bearer '+row['api_key']}
            body = {'model':row['model'], 'messages':messages, 'stream':True, 'store':False,
                'max_completion_tokens':6000, 'response_format':{'type':'json_object'}}
        else:
            url = 'https://api.anthropic.com/v1/messages'
            headers = {'x-api-key':row['api_key'], 'anthropic-version':'2023-06-01'}
            body = {'model':row['model'], 'system':messages[0]['content'], 'messages':messages[1:],
                'max_tokens':6000, 'stream':True}
        raw, complete, tokens = '', False, {}
        try:
            with httpx.Client(timeout=httpx.Timeout(600, connect=20), trust_env=False, follow_redirects=False, transport=self.transport) as client:
                with client.stream('POST', url, headers=headers, json=body) as response:
                    if response.status_code in (401, 403): raise NoteFailure('provider_authentication')
                    if response.status_code == 429: raise NoteFailure('provider_limit')
                    response.raise_for_status()
                    received = 0
                    for line in response.iter_lines():
                        received += len(line.encode())
                        if received > 2_000_000: raise NoteFailure('invalid_output')
                        if not line.startswith('data:'): continue
                        data = line[5:].strip()
                        if data == '[DONE]': break
                        event = json.loads(data)
                        delta = ''
                        if provider == 'openai':
                            for choice in event.get('choices', []):
                                message = choice.get('delta', {})
                                if message.get('tool_calls') or message.get('refusal'): raise NoteFailure('invalid_output')
                                delta += message.get('content') or ''
                                if choice.get('finish_reason'):
                                    if choice['finish_reason'] != 'stop': raise NoteFailure('truncated_output')
                                    complete = True
                            if event.get('usage'): tokens = event['usage']
                        else:
                            kind = event.get('type')
                            if kind == 'error': raise NoteFailure('model_unavailable')
                            if kind == 'content_block_start' and event['content_block']['type'] != 'text':
                                raise NoteFailure('invalid_output')
                            if kind == 'content_block_delta': delta = event.get('delta', {}).get('text', '')
                            if kind == 'message_delta':
                                if event.get('delta', {}).get('stop_reason') != 'end_turn': raise NoteFailure('truncated_output')
                                complete = True; tokens = event.get('usage', {})
                        raw += delta
                        if on_preview and delta: on_preview(preview_text(raw))
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise NoteFailure('model_unavailable') from None
        if not complete: raise NoteFailure('truncated_output')
        return raw, tokens

    def save_connection(self, provider, model, api_key='', executable=''):
        if self.bridge:
            try:
                return self.bridge.save(provider, model, api_key, executable)
            except ProviderBridgeError as exc:
                raise ValueError(exc.message) from None
        self.connections.save(provider, model, api_key, executable)
        return {'provider': provider}

    def remove_connection(self, provider):
        if self.bridge:
            try:
                return self.bridge.remove(provider)
            except ProviderBridgeError as exc:
                raise ValueError(exc.message) from None
        self.connections.remove(provider)
        return {'provider': provider}

    def sign_in_connection(self, provider):
        if self.bridge:
            try:
                return self.bridge.sign_in(provider)
            except ProviderBridgeError as exc:
                raise ValueError(exc.message) from None
        from .subscription_notes import sign_in
        row = self.connections.read(provider)
        if not row:
            raise ValueError('Save the subscription connection before signing in.')
        sign_in(provider, row['executable'], str(self.connections.directory))
        return {'provider': provider}

    def sign_out_connection(self, provider):
        if self.bridge:
            try:
                return self.bridge.sign_out(provider)
            except ProviderBridgeError as exc:
                raise ValueError(exc.message) from None
        from .subscription_notes import sign_out
        row = self.connections.read(provider)
        if not row:
            raise ValueError('This subscription is not connected.')
        sign_out(provider, row['executable'], str(self.connections.directory))
        self.connections.remove(provider)
        return {'provider': provider}
