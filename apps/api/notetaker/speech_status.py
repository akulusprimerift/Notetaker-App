"""Ephemeral native-worker readiness; never infer readiness from model files alone."""
import json
import time
from pathlib import Path
from threading import Event, Thread

from .speech_provider import model_files_available


def speech_status(settings):
    if not settings or not model_files_available(settings.speech_model_path):
        return {'state': 'missing', 'name': None}
    result = {'state': 'selected', 'name': Path(settings.speech_model_path).name}
    if settings.speech_status_path:
        try:
            status = json.loads(Path(settings.speech_status_path).read_text(encoding='utf-8'))
            if (status['session'] == settings.speech_status_session
                    and status['model'] == settings.speech_model_path
                    and 0 <= time.time() - status['updated'] < 15):
                result['state'] = 'ready' if status['ready'] else 'failed' if status.get('failed') else 'loading'
            else:
                result['state'] = 'offline'
        except (OSError, ValueError, KeyError, TypeError):
            result['state'] = 'offline'
    return result


def start_status(settings, provider):
    stopped = Event()
    def publish():
        if not settings.speech_status_path:
            return
        target = Path(settings.speech_status_path)
        temporary = target.with_suffix('.tmp')
        while not stopped.is_set():
            try:
                temporary.write_text(json.dumps({'session': settings.speech_status_session,
                    'model': settings.speech_model_path, 'updated': time.time(),
                    'ready': provider.model is not None and hasattr(provider, 'metadata'),
                    'failed': getattr(provider, 'load_failed', False)}), encoding='utf-8')
                temporary.replace(target)
            except OSError:
                pass  # Status failure cannot stop audio processing.
            stopped.wait(3)
    thread = Thread(target=publish, daemon=True)
    thread.start()
    return stopped
