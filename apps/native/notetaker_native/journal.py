"""Durable recording queue. A receipt releases bytes only after every field matches."""
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import wave
from contextlib import contextmanager


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, lecture TEXT NOT NULL,
                metadata TEXT NOT NULL, stopped INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS chunks(run TEXT NOT NULL, sequence INTEGER NOT NULL,
                identity TEXT NOT NULL, audio BLOB, PRIMARY KEY(run, sequence));''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def start(self, lecture, manifest, grant):
        with self.connect() as db:
            db.execute('INSERT INTO runs(id, lecture, metadata) VALUES(?,?,?)',
                       (manifest['id'], lecture, json.dumps({**manifest, 'grant':grant})))

    def append(self, run, pcm):
        if not pcm or len(pcm) % 2:
            raise ValueError('Invalid PCM frame')
        with self.connect() as db:
            row = db.execute('SELECT metadata,stopped FROM runs WHERE id=?', (run,)).fetchone()
            if not row or row[1]:
                raise RuntimeError('This recording is closed')
            metadata = json.loads(row[0])
            previous = db.execute('SELECT identity FROM chunks WHERE run=? ORDER BY sequence DESC LIMIT 1', (run,)).fetchone()
            previous = json.loads(previous[0]) if previous else None
            pending = db.execute('SELECT COALESCE(SUM(LENGTH(audio)),0) FROM chunks').fetchone()[0]
            if pending+len(pcm) > 1024**3:
                raise RuntimeError('Local recovery storage is full. Recording stopped; saved audio is retained.')
            with io.BytesIO() as buffer:
                with wave.open(buffer, 'wb') as audio:
                    audio.setparams((1, 2, metadata['sample_rate'], 0, 'NONE', ''))
                    audio.writeframes(pcm)
                raw = buffer.getvalue()
            identity = {'run_id':run, 'capture_epoch':metadata['capture_epoch'],
                        'sequence':previous['sequence']+1 if previous else 0,
                        'start_sample':previous['start_sample']+previous['sample_count'] if previous else 0,
                        'sample_count':len(pcm)//2, 'sample_rate':metadata['sample_rate'], 'channels':1,
                        'encoding':'pcm_s16le_wav', 'sha256':hashlib.sha256(raw).hexdigest(), 'byte_length':len(raw)}
            db.execute('INSERT INTO chunks VALUES(?,?,?,?)', (run, identity['sequence'], json.dumps(identity), raw))
            return identity

    def stop(self, run):
        with self.connect() as db:
            db.execute('UPDATE runs SET stopped=1 WHERE id=?', (run,))

    def gap(self, run, reason):
        if reason not in ('microphone_lost','sleep_or_suspension','storage_failure'):
            raise ValueError('Unknown recording gap')
        boundary = self.seal(run)['final_sample_count']
        with self.connect() as db:
            row = db.execute('SELECT metadata FROM runs WHERE id=?',(run,)).fetchone()
            metadata = json.loads(row[0])
            metadata['gaps'] = [*metadata.get('gaps',[]),
                                {'reason':reason,'after_sample':boundary,'unknown_extent':True}]
            db.execute('UPDATE runs SET metadata=? WHERE id=?',(json.dumps(metadata),run))

    def acknowledge(self, identity, receipt):
        if receipt.get('storage_state') != 'verified' or any(receipt.get(k) != v for k, v in identity.items()):
            raise RuntimeError('Audio receipt did not match. The local copy is retained.')
        with self.connect() as db:
            db.execute('UPDATE chunks SET audio=NULL WHERE run=? AND sequence=? AND identity=?',
                       (identity['run_id'], identity['sequence'], json.dumps(identity)))

    def pending(self, run):
        with self.connect() as db:
            return [(json.loads(i), raw) for i, raw in db.execute(
                'SELECT identity,audio FROM chunks WHERE run=? AND audio IS NOT NULL ORDER BY sequence', (run,))]

    def runs(self):
        with self.connect() as db:
            return [dict(json.loads(meta), lecture=lecture, stopped=bool(stopped))
                    for lecture, meta, stopped in db.execute('SELECT lecture,metadata,stopped FROM runs')]

    def seal(self, run):
        with self.connect() as db:
            row = db.execute('SELECT identity FROM chunks WHERE run=? ORDER BY sequence DESC LIMIT 1', (run,)).fetchone()
            metadata = db.execute('SELECT metadata FROM runs WHERE id=?',(run,)).fetchone()
        last = json.loads(row[0]) if row else None
        return {'last_sequence':last['sequence'] if last else -1,
                'final_sample_count':last['start_sample']+last['sample_count'] if last else 0,
                'gaps':json.loads(metadata[0]).get('gaps',[]) if metadata else []}

    def purge(self, lecture):
        with self.connect() as db:
            db.execute('PRAGMA secure_delete=ON')
            db.execute('DELETE FROM chunks WHERE run IN (SELECT id FROM runs WHERE lecture=?)', (lecture,))
            db.execute('DELETE FROM runs WHERE lecture=?', (lecture,))
