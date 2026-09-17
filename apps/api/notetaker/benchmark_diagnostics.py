"""Synthetic SQLite monitoring cost experiment; never opens the student library."""
import argparse
import json
import math
import platform
import statistics
import tempfile
from datetime import timedelta
from pathlib import Path
from time import perf_counter
import tracemalloc

import sqlalchemy
from sqlalchemy import insert

from .db import database
from .diagnostics import processing_snapshot
from .models import Base, Course, Job, Lecture, Owner, now


def run_case(size, samples):
    with tempfile.TemporaryDirectory(prefix='notetaker-scale-') as directory:
        engine, sessions = database('sqlite:///' + (Path(directory) / 'synthetic.db').as_posix())
        try:
            Base.metadata.create_all(engine)
            stamp = now()
            with sessions() as db:
                db.add(Owner(id='synthetic-owner'))
                db.flush()
                db.add(Course(id='synthetic-course', owner_id='synthetic-owner', name='Synthetic'))
                db.flush()
                db.add_all([Lecture(id=f'lecture-{i}', course_id='synthetic-course', title='Synthetic') for i in range(100)])
                db.flush()
                for start in range(0, size, 1000):
                    db.execute(insert(Job), [{'id': str(i), 'lecture_id': f'lecture-{i % 100}',
                        'logical_key': str(i), 'kind': ['speech.window', 'notes.generate', 'learning.generate'][i % 3],
                        'status': 'due' if i % 10 == 0 else 'completed', 'lifecycle_epoch': 1,
                        'audio_epoch': 1, 'input_revision': 'synthetic',
                        'due_at': stamp - timedelta(seconds=60)} for i in range(start, min(size, start + 1000))])
                db.commit()
            durations = []
            for _ in range(samples + 1):
                with sessions() as db:
                    started = perf_counter()
                    snapshot = processing_snapshot(db, 'synthetic-owner', sampled_at=stamp)
                    durations.append((perf_counter() - started) * 1000)
                    assert sum(row['count'] for row in snapshot['groups']) == (size + 9) // 10
            tracemalloc.start()
            try:
                with sessions() as db:
                    processing_snapshot(db, 'synthetic-owner', sampled_at=stamp)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            warm = sorted(durations[1:])
            return {'jobs': size, 'active_jobs': (size + 9) // 10, 'lectures': 100,
                'first_query_ms': round(durations[0], 3), 'warm_samples': samples,
                'warm_median_ms': round(statistics.median(warm), 3),
                'warm_p95_ms': round(warm[math.ceil(.95 * samples) - 1], 3),
                'python_allocation_peak_bytes': peak,
                'response_bytes': len(json.dumps(snapshot).encode()), 'returned_groups': len(snapshot['groups'])}
        finally:
            engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'experiment': 'processing-diagnostics-history-growth-v1',
        'environment': {'os': platform.platform(), 'python': platform.python_version(),
            'sqlalchemy': sqlalchemy.__version__, 'database': 'isolated temporary SQLite WAL'},
        'workload': '100 lectures, 10% due and 90% completed, three job kinds; no inference or audio',
        'limits': 'Serial warm queries; first query is not a cold-disk measurement. Python allocations exclude native database memory. No PostgreSQL, contention, inference, or end-to-end latency qualification.',
        'results': [run_case(size, 20) for size in (1000, 10000, 100000)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
