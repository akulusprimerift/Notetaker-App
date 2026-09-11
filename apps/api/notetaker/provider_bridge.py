"""Authenticated loopback bridge to the Electron host's protected connections."""
import httpx

from .note_provider import NoteFailure, preview_text


class ProviderBridgeError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


class ProviderBridge:
    def __init__(self, url, token):
        self.url, self.token = url.rstrip('/'), token

    def request(self, method, path, body=None, timeout=10):
        try:
            with httpx.Client(base_url=self.url, timeout=timeout, trust_env=False, follow_redirects=False) as client:
                response = client.request(method, path, json=body, headers={'X-Notetaker-Bridge-Token': self.token})
        except httpx.HTTPError:
            raise ProviderBridgeError('provider_bridge_unavailable', 'The desktop provider bridge is unavailable. Restart Notetaker.') from None
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400:
            raise ProviderBridgeError(payload.get('code', 'provider_connection_failed'),
                                      payload.get('message', 'The provider connection could not be completed.'))
        if not isinstance(payload, dict):
            raise ProviderBridgeError('provider_bridge_invalid', 'The desktop provider bridge returned an invalid response.')
        return payload

    def inventory(self):
        try:
            return self.request('GET', '/connections', timeout=5).get('connections', [])
        except ProviderBridgeError as exc:
            raise NoteFailure(exc.code) from None

    def verify(self, model, expected=None):
        try:
            row = self.request('POST', '/connections/verify', {'model': model, 'digest': expected}, timeout=10)
            return {'name': model, 'digest': row['digest']}, {'model': model.split('/', 1)[1], 'id': row['digest'], 'bridge': True}
        except (ProviderBridgeError, KeyError, TypeError):
            raise NoteFailure('connection_unavailable') from None

    def save(self, provider, model, api_key='', executable=''):
        return self.request('POST', '/connections', {'provider': provider, 'model': model,
            'api_key': api_key, 'executable': executable}, timeout=10)

    def remove(self, provider):
        return self.request('DELETE', '/connections/' + provider, timeout=10)

    def sign_in(self, provider):
        return self.request('POST', '/connections/' + provider + '/sign-in', timeout=210)

    def sign_out(self, provider):
        return self.request('POST', '/connections/' + provider + '/sign-out', timeout=45)

    def generate(self, model, digest, messages, on_preview=None):
        try:
            result = self.request('POST', '/connections/generate', {'model': model, 'digest': digest, 'messages': messages}, timeout=610)
            raw = result['raw']
            if on_preview:
                on_preview(preview_text(raw))
            return raw, result.get('metrics', {})
        except ProviderBridgeError as exc:
            raise NoteFailure(exc.code) from None
        except (KeyError, TypeError):
            raise NoteFailure('provider_unavailable') from None
