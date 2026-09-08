"""Reproducible, opt-in local-model evaluation using synthetic CS text only."""
import argparse
import json
import platform
import time
from pathlib import Path
from types import SimpleNamespace
from .config import Settings
from .note_provider import OllamaNotes
from .note_contract import ROOT, validate_notes
from .note_draft import DRAFT_PROMPT as PROMPT
from .security import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='qwen3:4b')
    parser.add_argument('--case', default='all')
    parser.add_argument('--dataset', choices=['cs', 'universal'], default='cs')
    parser.add_argument('--report', default='.local/note-evaluation.json')
    args = parser.parse_args()
    filename = 'cs-notes-v1.json' if args.dataset == 'cs' else 'universal-notes-v1.json'
    raw = (ROOT/'evaluations/fixtures'/filename).read_text(encoding='utf-8')
    dataset = json.loads(raw)
    cases = [c for c in dataset['cases'] if args.case == 'all' or c['id'] == args.case]
    if not cases: parser.error('Unknown synthetic case')
    provider = OllamaNotes(Settings())
    model, _ = provider.verify(args.model)
    preference = SimpleNamespace(model=model['name'], model_digest=model['digest'])
    report = {'origin': 'synthetic_text', 'model': model, 'prompt_sha256': digest(PROMPT),
        'dataset_sha256': digest(raw), 'platform': platform.platform(), 'cases': [],
        'human_review': 'pending', 'release_eligible': False}
    destination = Path(args.report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        print('Evaluating synthetic case:', case['id'], flush=True)
        evidence = {key: case['input'][key] for key in ('source_snapshot_id', 'settings_version', 'allow_ai_explanations', 'profile', 'sources')}
        result = {'id': case['id'], 'contract_valid': False}
        started = time.monotonic()
        try:
            output, metadata = provider.generate(evidence, preference)
            result.update(output=output, metadata=metadata)
            result['resolved_citations'] = validate_notes(output, evidence)
            result['contract_valid'] = True
        except Exception as exc:
            result['error_code'] = getattr(exc, 'code', type(exc).__name__)
        result['seconds'] = round(time.monotonic() - started, 2)
        report['cases'].append(result)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(case['id'], 'passed' if result['contract_valid'] else 'rejected', result['seconds'], 'seconds', flush=True)
    return 0 if all(c['contract_valid'] for c in report['cases']) else 1


if __name__ == '__main__': raise SystemExit(main())
