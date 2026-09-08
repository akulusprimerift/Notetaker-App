"""Inspect actual saved synthetic notes through authenticated local HTTP routes."""
import argparse
import io
import json
import secrets
import wave
from datetime import timedelta
from pathlib import Path
import httpx
from .config import Settings
from .db import database
from .models import Lecture, Course, Session, NoteRevision, NoteRequest, now
from .notes import inputs
from .note_contract import validate_notes
from .security import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lecture', required=True)
    parser.add_argument('--report', default='.local/saved-note-verification.json')
    args = parser.parse_args()
    settings = Settings()
    engine, sessions = database(settings.database_url)
    token = secrets.token_urlsafe(40)
    try:
        with sessions() as db:
            lecture = db.get(Lecture, args.lecture)
            if not lecture or 'synthetic' not in lecture.title.lower(): raise RuntimeError('Use an explicitly synthetic test lecture')
            course = db.get(Course, lecture.course_id)
            if course.code not in ('M03 TEST', 'M04 TEST'): raise RuntimeError('Use a synthetic evaluation course')
            db.add(Session(token_hash=digest(token), owner_id=course.owner_id, csrf_hash=digest(secrets.token_urlsafe(32)),
                expires_at=now()+timedelta(minutes=2)))
            db.commit()
        prefix = f'/lectures/{args.lecture}'
        with httpx.Client(base_url='http://127.0.0.1:8010', cookies={'nt_session':token}, timeout=30, trust_env=False) as client:
            response = client.get(prefix+'/notes'); response.raise_for_status(); state = response.json()
            if state['status'] != 'ready' or state['stale']: raise RuntimeError('Current notes are not ready')
            revision = state['revision']
            if revision['metadata']['provider'] != 'ollama_local': raise RuntimeError('An actual local model is required')
            with sessions() as db:
                saved = db.get(NoteRevision, revision['id'])
                evidence = inputs(db, db.get(NoteRequest, saved.request_id))
                resolved = validate_notes(revision['content'], evidence)
            export = client.get(prefix+'/notes/revisions/'+revision['id']+'/export'); export.raise_for_status()
            assert 'Source appendix' in export.text and '.md' in export.headers['content-disposition']
            audio_checks = []
            for source_id in dict.fromkeys(c['source_id'] for c in resolved):
                source = client.get(prefix+'/sources/'+source_id); source.raise_for_status(); source = source.json()
                audio = client.get(prefix+'/sources/'+source_id+'/audio'); audio.raise_for_status()
                with wave.open(io.BytesIO(audio.content), 'rb') as wav:
                    assert wav.getframerate() == source['sample_rate']
                    assert wav.getnframes() == source['end_sample']-source['start_sample']
                    audio_checks.append({'source_id':source_id,'frames':wav.getnframes(),'sample_rate':wav.getframerate()})
            report = {'origin':'synthetic_speech','lecture_id':args.lecture,'checked_at':now().isoformat()+'Z',
                'state':state,'input':evidence,'canonical_valid':True,'audio_checks':audio_checks,
                'export_bytes':len(export.content),'human_review':'pending','release_eligible':False}
            destination = Path(args.report); destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            destination.with_suffix('.md').write_text(export.text,encoding='utf-8')
            print(f'Actual revision {revision["revision"]}: notes, Markdown and {len(audio_checks)} audio sources verified.')
    finally:
        with sessions() as db:
            session = db.get(Session, digest(token))
            if session: session.revoked = True; db.commit()
        engine.dispose()


if __name__ == '__main__': main()
