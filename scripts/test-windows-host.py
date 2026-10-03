"""Isolated real-service synthetic smoke and lecture-workflow qualification.

Runs the frozen Windows or Mac service host against a new profile. It never opens
the student library, accesses a microphone, downloads models or calls providers.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import queue
import secrets
import subprocess
import sys
import threading
import time
import wave
from uuid import uuid4

import httpx

ORIGIN = 'http://127.0.0.1:3000'
SYLLABUS = '''# Synthetic course syllabus
Week 3: hash tables, collision resolution and load factor.
Key term: amortized analysis means averaging cost over a sequence of operations.
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('resources', type=Path)
    parser.add_argument('--source-host', action='store_true')
    parser.add_argument('--speech-model', type=Path)
    parser.add_argument('--synthetic-audio', type=Path, help='Mono PCM16 WAV; omit --speech-model to check the missing-model path')
    parser.add_argument('--note-model')
    parser.add_argument('--fast', action='store_true', help='Upload without real-time pacing (no live latency claim)')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    profile = Path('.local') / ('host-smoke-' + uuid4().hex)
    profile.mkdir(parents=True)
    config = {'resources': str(args.resources.resolve()), 'data': str(profile.resolve()),
        'secret': secrets.token_hex(32), 'speechPath': str(args.speech_model.resolve()) if args.speech_model else ''}
    service = 'NotetakerService.exe' if sys.platform == 'win32' else 'NotetakerService'
    executable = [sys.executable, str(Path('apps/api/windows_service.py').resolve())] if args.source_host else [str(args.resources.resolve() / 'service' / service)]
    started = time.monotonic()
    child = subprocess.Popen([*executable, 'host'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), env=os.environ.copy())
    messages = queue.Queue()
    def read(stream):
        for line in stream:
            messages.put(line)
    threading.Thread(target=read, args=(child.stdout,), daemon=True).start()
    threading.Thread(target=read, args=(child.stderr,), daemon=True).start()
    try:
        child.stdin.write(json.dumps(config) + '\n')
        child.stdin.flush()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f'Host stopped: {child.returncode}; inspect {profile}')
            try:
                line = messages.get(timeout=1)
            except queue.Empty:
                continue
            print(line.strip(), flush=True)
            value = json.loads(line)
            if value.get('status') == 'failed':
                raise RuntimeError(value['message'])
            if value.get('status') == 'ready':
                break
        else:
            raise RuntimeError('Startup deadline expired')
        startup_seconds = round(time.monotonic() - started, 2)
        with httpx.Client(base_url='http://127.0.0.1:8010', timeout=120, trust_env=False) as client:
            response = client.post('/session/open', headers={'origin': ORIGIN})
            response.raise_for_status()
            csrf = response.json()['csrf_token']
            def headers(extra=None):
                return {'origin': ORIGIN, 'x-csrf-token': csrf, 'idempotency-key': str(uuid4()), **(extra or {})}
            response = client.post('/courses', json={'name': 'Synthetic standalone service smoke', 'code': 'TEST'}, headers=headers())
            response.raise_for_status()
            assert client.get('/courses').json()[0]['name'] == 'Synthetic standalone service smoke'
            if args.synthetic_audio:
                report = workflow(client, headers, response.json(), args, profile)
                report['startup_seconds'] = startup_seconds
                (profile / 'workflow-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(report, indent=2), flush=True)
        print(json.dumps({'host': 'passed', 'postgres_api_write_read': 'passed', 'profile': str(profile)}), flush=True)
    finally:
        child.stdin.close()
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)


def workflow(client, headers, course, args, profile):
    """Saved audio → live transcript/notes → edits/regeneration → prompted flash cards → exports → finalize."""
    def ok(response):
        if response.is_error:
            raise RuntimeError(f'{response.request.method} {response.request.url.path}: {response.status_code} {response.text}')
        return response
    def post(route, body, extra=None):
        return ok(client.post(route, json=body, headers=headers(extra))).json()
    def wait(label, check, timeout=args.timeout, interval=1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = check()
            if value:
                return value
            time.sleep(interval)
        raise RuntimeError(label + ' deadline expired')

    with wave.open(str(args.synthetic_audio), 'rb') as audio:
        assert audio.getnchannels() == 1 and audio.getsampwidth() == 2, 'Expected mono PCM16 WAV'
        rate = audio.getframerate(); pcm = audio.readframes(audio.getnframes())
    samples = len(pcm) // 2
    report = {'synthetic_only': True, 'microphone_access': False, 'paced_real_time': not args.fast,
        'platform': sys.platform, 'machine': platform.machine(), 'os': platform.platform(),
        'processor': platform.processor(), 'logical_cpus': os.cpu_count(),
        'speech_model': args.speech_model.name if args.speech_model else None, 'note_model': args.note_model,
        'audio_seconds': round(samples / rate, 2), 'sample_rate': rate, 'profile': str(profile)}
    lecture = post('/courses/' + course['id'] + '/lectures', {'title': 'Synthetic lecture workflow — no microphone'})
    path = '/lectures/' + lecture['id']
    ok(client.put(path + '/audio-retention', json={'keep_audio': True}, headers=headers()))
    material = post(path + '/materials', {'name': 'synthetic-syllabus.md', 'kind': 'syllabus',
        'data': base64.b64encode(SYLLABUS.encode()).decode(), 'expected_count': 0})
    assert any(row['id'] == material['id'] for row in ok(client.get(path + '/materials')).json())
    report['material_saved'] = True

    missing_speech = args.speech_model is None
    if missing_speech:
        assert ok(client.get(path + '/transcript')).json()['speech_model']['state'] == 'missing'
    else:
        assert args.note_model, 'Select an existing local note model for the workflow'
        began = time.monotonic()
        def speech_ready():
            status = ok(client.get(path + '/transcript')).json()['speech_model']
            assert status['state'] != 'failed', status
            return status['state'] == 'ready'
        wait('Speech readiness', speech_ready, 300)
        report['speech_ready_seconds'] = round(time.monotonic() - began, 2)
        missing = client.post(path + '/notes/model', json={'expected_version': 0, 'model': 'notetaker-missing-model:0'}, headers=headers())
        assert missing.status_code == 503 and missing.json()['error']['code'] == 'model_unavailable', missing.text
        report['missing_note_model_refused'] = True
        post(path + '/notes/model', {'expected_version': 0, 'model': args.note_model})

    grant = secrets.token_urlsafe(48)
    run = post(path + '/capture-runs', {'grant': grant, 'sample_rate': rate, 'expected_capture_epoch': 0})
    capture = {'X-Capture-Grant': grant}
    timeline = {'first_preview': None, 'first_passage': None, 'first_revision': None, 'preview_updates': 0,
        'concurrent_samples': 0, 'max_delay': 0.0}
    stop = threading.Event()
    started = time.monotonic()
    def elapsed():
        return round(time.monotonic() - started, 2)
    def watch():
        try:
            with httpx.Client(base_url='http://127.0.0.1:8010', cookies=client.cookies, timeout=30, trust_env=False) as watcher:
                with watcher.stream('GET', path + '/notes/stream') as response:
                    for line in response.iter_lines():
                        if stop.is_set():
                            return
                        if not line.startswith('data: '):
                            continue
                        if json.loads(line[6:]).get('text'):
                            timeline['preview_updates'] += 1
                            timeline['first_preview'] = timeline['first_preview'] or elapsed()
                            timeline['last_preview'] = time.monotonic()
        except Exception as exc:  # The report records stream loss; checks below still decide pass/fail.
            timeline['stream_error'] = type(exc).__name__
    def poll():
        # The PostgreSQL host's note stream omits transcript state; poll it as the workspace does.
        with httpx.Client(base_url='http://127.0.0.1:8010', cookies=client.cookies, timeout=30, trust_env=False) as poller:
            while not stop.is_set():
                transcript = poller.get(path + '/transcript').json()
                counts = transcript['counts']
                timeline['max_delay'] = max(timeline['max_delay'], transcript['processing_delay_seconds'])
                if (transcript.get('snapshot') or {}).get('segments') and timeline['first_passage'] is None:
                    timeline['first_passage'] = elapsed()
                if (counts['running'] or counts['due']) and time.monotonic() - timeline.get('last_preview', 0) < 1:
                    timeline['concurrent_samples'] += 1
                time.sleep(0.5)
    for target in (watch, poll):
        threading.Thread(target=target, daemon=True).start()

    chunks, sequence, uploads = [], 0, []
    for start in range(0, samples, 2 * rate):
        count = min(2 * rate, samples - start)
        if not args.fast:
            time.sleep(max(0, (start + count) / rate - (time.monotonic() - started)))
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(rate); audio.writeframes(pcm[start * 2:(start + count) * 2])
        raw = buffer.getvalue()
        identity = {'run_id': run['id'], 'capture_epoch': run['capture_epoch'], 'sequence': sequence,
            'start_sample': start, 'sample_count': count, 'sample_rate': rate, 'channels': 1,
            'encoding': 'pcm_s16le_wav', 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw)}
        sent = time.monotonic()
        receipt = ok(client.put(path + '/capture-runs/' + run['id'] + '/chunks/' + str(sequence), content=raw,
            headers={**headers(capture), 'X-Chunk-Identity': json.dumps(identity), 'Content-Type': 'audio/wav'})).json()
        uploads.append(time.monotonic() - sent)
        assert receipt['storage_state'] == 'verified', receipt
        chunks.append((receipt['chunk_id'], identity['sha256']))
        # The recorder renews its capture lease the same way during a real lecture.
        ok(client.post(path + '/capture-runs/' + run['id'] + '/heartbeat', json={}, headers=headers(capture)))
        if timeline['first_revision'] is None and ok(client.get(path + '/notes')).json().get('revision'):
            timeline['first_revision'] = elapsed()
        sequence += 1
    capture_end = elapsed()
    manifest = ok(client.get(path + '/capture-runs/' + run['id'] + '/manifest')).json()
    post(path + '/capture-runs/' + run['id'] + '/seal', {'expected_version': manifest['manifest_version'],
        'last_sequence': sequence - 1, 'final_sample_count': samples, 'gaps': []}, capture)
    report.update(chunks_verified=len(chunks), upload_p50_seconds=round(sorted(uploads)[len(uploads) // 2], 3),
        upload_max_seconds=round(max(uploads), 3), capture_end_seconds=capture_end)

    def audio_intact():
        for chunk, digest in chunks:
            body = ok(client.get(path + '/audio-chunks/' + chunk)).content
            assert hashlib.sha256(body).hexdigest() == digest, 'Saved audio changed'
        return True

    if missing_speech:
        transcript = wait('Missing-model status', lambda: (lambda t: t if 'model_unavailable' in t['errors'] else None)(
            ok(client.get(path + '/transcript')).json()), 120)
        assert not (transcript.get('snapshot') or {}).get('segments')
        stop.set()
        report.update(missing_speech_model_visible=True, transcript_status=transcript['status'], audio_intact=audio_intact())
        return report

    def settled():
        transcript = ok(client.get(path + '/transcript')).json()
        notes = ok(client.get(path + '/notes')).json()
        if timeline['first_revision'] is None and notes.get('revision'):
            timeline['first_revision'] = elapsed()
        if transcript['status'] == 'needs_attention' or notes['status'] == 'needs_attention':
            raise RuntimeError(f"Processing failed: {transcript['errors']} {notes.get('error_code')}")
        if transcript['status'] == 'processed' and 'transcript_done' not in timeline:
            timeline['transcript_done'] = elapsed()
        if transcript['status'] == 'processed' and notes['status'] == 'ready' and not notes['stale']:
            return transcript, notes
        return None
    transcript, notes = wait('Transcript and notes', settled)
    stop.set()
    segments = transcript['snapshot']['segments']
    revision = notes['revision']
    report.update(passages=len(segments), first_streamed_preview_seconds=timeline['first_preview'],
        first_passage_seconds=timeline['first_passage'], first_saved_notes_seconds=timeline['first_revision'],
        notes_saved_before_capture_end=bool(timeline['first_revision'] and timeline['first_revision'] <= capture_end),
        preview_updates=timeline['preview_updates'], previews_while_speech_pending_polls=timeline['concurrent_samples'],
        max_processing_delay_seconds=timeline['max_delay'], stream_error=timeline.get('stream_error'),
        transcript_lag_after_capture_seconds=round(timeline['transcript_done'] - capture_end, 2),
        notes_lag_after_capture_seconds=round(elapsed() - capture_end, 2), note_revision=revision['revision'],
        saved_sections=notes['processing']['saved_sections'])

    # Citations resolve to saved transcript passages or the uploaded material.
    citations = revision['resolved_citations']
    known = {s['id'] for s in segments}
    assert citations and all(c['source_id'] in known or c['source_id'].startswith('material:') for c in citations), citations
    transcript_source = next(c['source_id'] for c in citations if c['source_id'] in known)
    ok(client.get(path + '/sources/' + transcript_source))
    ok(client.get(path + '/sources/' + transcript_source + '/audio'))
    report.update(citations=len(citations), material_citations=sum(c['source_id'].startswith('material:') for c in citations))

    # Protected edit survives a regenerated suggestion; merge and undo keep it.
    marker = ' Synthetic student edit marker'  # No Markdown-escaped characters.
    passage = revision['content']['blocks'][0]['passages'][0]
    saved = post(path + '/notes/edits', {'expected_version': 0, 'base_id': revision['id'], 'action': 'save',
        'passages': [{'id': passage['id'], 'text': passage['text'] + marker}]})
    preference = notes['preference']
    post(path + '/notes/model', {'expected_version': preference['version'], 'model': args.note_model,
        'detail_prompt': 'Include every definition and worked step; keep source citations.'})
    regen_began = time.monotonic()
    def proposal():
        editing = ok(client.get(path + '/notes')).json()['editing']
        return editing if editing['proposal'] and editing['proposal_valid'] else None
    editing = wait('Regeneration proposal', proposal)
    report['regeneration_seconds'] = round(time.monotonic() - regen_began, 2)
    def has_marker(content):
        return any(marker in p['text'] for b in content['blocks'] for p in b['passages'])
    assert has_marker(editing['selected']['content']), 'Student edit was overwritten'
    merged = post(path + '/notes/edits', {'expected_version': editing['version'], 'base_id': saved['id'], 'action': 'merge',
        'proposal_id': editing['proposal']['id'], 'block_ids': [editing['proposal']['content']['blocks'][0]['id']]})
    assert has_marker(merged['content']) and len(merged['content']['blocks']) > len(saved['content']['blocks'])
    undone = post(path + '/notes/edits', {'expected_version': merged['revision'], 'base_id': merged['id'],
        'action': 'undo', 'target_id': saved['id']})
    assert has_marker(undone['content']) and len(undone['content']['blocks']) == len(saved['content']['blocks'])
    report.update(protected_edit=True, merge=True, undo=True)

    # One explicit instruction generates a persisted set from the current selected saved notes.
    setup = ok(client.get(path + '/study/questions')).json()
    assert setup['revision_id'] == undone['id'] and setup['has_notes'] and setup['enabled'], setup
    prompt = 'Make concise flash cards for the key ideas. Keep every condition, exception and worked step.'
    queued = post(path + '/study/questions', {'revision_id': setup['revision_id'],
        'preference_id': setup['preference_id'], 'prompt': prompt})
    assert queued['prompt'] == prompt and queued['model'] == args.note_model
    def saved_flash_cards():
        result = ok(client.get(path + '/study/questions/' + queued['id'])).json()
        if result['status'] in ('failed', 'cancelled'):
            raise RuntimeError('Flash card generation failed: ' + str(result['error_code']))
        return result if result['status'] == 'completed' else None
    deck = wait('Prompted flash card generation', saved_flash_cards)
    assert deck['revision_id'] == setup['revision_id'] and deck['questions'], deck
    sources = {source['id']: source['text'] for source in deck['sources']}
    for card in deck['questions']:
        assert card['kind'] == 'flashcard'
        assert card['citations'] and all(citation['source_id'] in sources
            and citation['quote'] in sources[citation['source_id']] for citation in card['citations']), card
    card = deck['questions'][0]
    reviewed = post(path + '/study/questions/' + queued['id'] + '/' + card['id'] + '/reviews', {
        'question_revision': card['revision_id'], 'expected_version': card['review']['version'], 'rating': 'confident'})
    assert reviewed['version'] == card['review']['version'] + 1
    report.update(flash_card_prompt_submitted=True, flash_cards=len(deck['questions']),
        flash_card_provenance=True, self_assessment=True)

    # Exports of the selected student revision and generated revision.
    for format in ('markdown', 'docx'):
        body = ok(client.get(path + '/notes/edits/' + undone['id'] + '/export', params={'format': format})).content
        assert marker.strip().encode() in body if format == 'markdown' else body[:2] == b'PK'
        (profile / ('student-notes.' + ('md' if format == 'markdown' else format))).write_bytes(body)
    ok(client.get(path + '/notes/revisions/' + revision['id'] + '/export'))

    # Finalize and export the immutable snapshot; audio stays byte-identical.
    for attempt in range(5):
        state = ok(client.get(path + '/finalization')).json()
        response = client.post(path + '/finalization', json={'expected_cursor': state['cursor'],
            'expected_edit_version': state['edit_version'], 'available_only': False}, headers=headers())
        if response.is_success:
            break
        if response.json()['error']['code'] != 'finalization_version' or attempt == 4:
            ok(response)
    snapshot = wait('Final snapshot', lambda: next((row['snapshot_id'] for row in
        ok(client.get(path + '/finalization')).json()['history'] if row.get('snapshot_id')), None), 600)
    body = ok(client.get(path + '/final-snapshots/' + snapshot + '/export', params={'format': 'markdown'})).content
    assert marker.strip().encode() in body, 'Final snapshot lost the selected student revision'
    (profile / 'final-snapshot.md').write_bytes(body)
    report.update(final_snapshot=True, audio_intact=audio_intact(), workflow='passed')
    return report


if __name__ == '__main__':
    main()
