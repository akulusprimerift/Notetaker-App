"""Synthetic question-quality diagnostics, never a substitute for human review."""
import argparse
import json
import platform
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from .note_contract import ROOT, compact
from .note_provider import OllamaNotes, NoteFailure
from .question_provider import generate_questions
from .security import digest


def diagnostics(case, questions):
    answers = '\n'.join(q['answer'] for q in questions)
    missing = [pattern for pattern in case['required_answer_patterns'] if not re.search(pattern, answers, re.I)]
    prohibited = [pattern for pattern in case['forbidden_answer_patterns'] if re.search(pattern, answers, re.I)]
    return {'missing_required_patterns': missing, 'forbidden_patterns_found': prohibited,
        'fixture_signals_pass': not missing and not prohibited,
        'limitation': 'Pattern checks can miss paraphrases and contextual negation; inspect every flagged answer and all source support manually.'}


def evidence_for(case):
    return {'revision_id': 'synthetic-note', 'block_id': case['id'], 'topic': case['topic'],
        'notes': [{'text': case['text'], 'student_edited': False}],
        'sources': [{'id': case['id'] + '-source', 'text': case['text']}], 'issues': [],
        'kind': 'mixed', 'count': 3, 'focus': case['focus']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='An already installed local Ollama model; never downloaded.')
    parser.add_argument('--case', default='all')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    dataset = json.loads((ROOT / 'evaluations/fixtures/questions-v1.json').read_text(encoding='utf-8'))
    cases = [c for c in dataset['cases'] if args.case in ('all', c['id'])]
    if not cases: parser.error('Unknown fixture case')
    provider = OllamaNotes(SimpleNamespace(ollama_url='http://127.0.0.1:11434'))
    # Ollama inventory excludes cloud proxy models; this harness cannot send to paid providers.
    installed, _ = provider.verify(args.model)
    pref = SimpleNamespace(model=args.model, model_digest=installed['digest'])
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'model': args.model,
        'model_digest': installed['digest'], 'dataset_sha256': digest(compact(dataset)),
        'fixture_origin': dataset['origin'], 'environment': {'system': platform.system(), 'python': platform.python_version()},
        'human_review': 'pending', 'learning_outcomes': 'not_measured', 'release_eligible': False, 'cases': []}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        started = time.monotonic()
        try:
            questions, metadata = generate_questions(provider, evidence_for(case), pref)
            result = {'id': case['id'], 'generation_status': 'completed', 'structural_citation_checks': 'passed', 'questions': questions,
                'metadata': metadata, 'diagnostics': diagnostics(case, questions), 'critical_review': case['critical_review'],
                'human_rubric': [{'question_id': q['id'], 'support': None, 'answerability': None,
                    'clarity': None, 'usefulness': None, 'reviewer': None, 'comment': ''} for q in questions]}
        except NoteFailure as exc:
            result = {'id': case['id'], 'generation_status': 'failed',
                'structural_citation_checks': 'failed' if exc.code == 'invalid_output' else 'not_run', 'error_code': exc.code}
        result['seconds'] = round(time.monotonic() - started, 2)
        report['cases'].append(result)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f"{case['id']}: {result['structural_citation_checks']} ({result['seconds']}s)", flush=True)
    print(f'Report saved: {output}. Human quality review and learning outcomes remain unqualified.', flush=True)


if __name__ == '__main__': main()
