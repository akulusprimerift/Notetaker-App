"""Frozen console worker entry point; children never initialize GUI controls."""
import sys
import time
from pathlib import Path


def main():
    mode = sys.argv[1]
    if mode == 'verify-speech':
        import io
        import json
        import wave
        from types import SimpleNamespace
        from notetaker.config import Settings
        from notetaker.speech_provider import WhisperProvider
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as audio:
            audio.setparams((1,2,16000,0,'NONE','')); audio.writeframes(b'\0\0'*16000)
        settings = Settings(speech_model_path=sys.argv[2])
        result = WhisperProvider(settings).transcribe(buffer.getvalue(),
            SimpleNamespace(core_start=0,core_end=16000,context_start=0,context_end=16000),16000)
        print(json.dumps(result))
        return
    if mode == 'material-parser':
        from notetaker.material_parser import main as parse
        sys.argv = [sys.argv[0], sys.argv[2]]
        parse()
        return
    if mode == 'migrate':
        from alembic.config import Config
        from alembic import command
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
        config = Config()
        config.set_main_option('script_location', str(root/'apps/api/migrations'))
        command.upgrade(config, 'head')
    elif mode == 'api':
        import uvicorn
        uvicorn.run('notetaker.main:app', host='127.0.0.1', port=int(sys.argv[2]), access_log=False)
    elif mode == 'notes':
        from notetaker.note_worker import main as notes
        notes()
    elif mode == 'speech':
        from notetaker.config import Settings
        from notetaker.db import database
        from notetaker.audio_store import AudioStore
        from notetaker.speech_provider import WhisperProvider
        from notetaker.speech_worker import plan_pending, claim, execute
        settings = Settings()
        engine, sessions = database(settings.database_url)
        store, provider = AudioStore(settings), WhisperProvider(settings)
        try:
            provider.load()
        except Exception:
            import logging
            logging.warning('Speech model unavailable; recording remains independent')
        try:
            while True:
                try:
                    plan_pending(sessions, store)
                    chosen = claim(sessions)
                    if chosen:
                        execute(sessions, store, provider, chosen)
                    else:
                        time.sleep(.5)
                except Exception:
                    import logging
                    logging.exception('Speech worker will retry; saved audio is retained')
                    time.sleep(2)
        finally:
            engine.dispose()
    else:
        raise ValueError('Unknown worker mode')


if __name__ == '__main__':
    main()
