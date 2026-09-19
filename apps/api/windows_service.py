"""Frozen Windows runtime entrypoint; no model provisioning or external fallback."""
import multiprocessing
from pathlib import Path
import sys


def main():
    role = sys.argv[1] if len(sys.argv) == 2 else ''
    if role == 'host':
        from notetaker.windows_host import entry
        return entry()
    if role == 'migrate':
        from alembic.config import Config
        from alembic import command
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
        config = Config()
        config.set_main_option('script_location', str(root / 'apps/api/migrations'))
        command.upgrade(config, 'head')
    elif role == 'api':
        import uvicorn
        from notetaker.main import create_app
        uvicorn.run(create_app(), host='127.0.0.1', port=8010, access_log=False)
    elif role == 'notes':
        from notetaker.note_worker import main as worker
        worker()
    elif role == 'speech':
        from notetaker.speech_worker import main as worker
        sys.argv = [sys.argv[0]]
        worker()
    else:
        raise SystemExit('Choose host, migrate, api, notes or speech.')
    return 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
