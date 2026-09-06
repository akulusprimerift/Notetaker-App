import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import {
  validateFixtureSet, validateNotes, validateSpeech, resolveCitation,
  buildNoteRequest, wordErrorRate, reviewSummary, providerNoteSchema, noteSchema,
} from '../../evaluations/lib/contracts.mjs';

const dataset = JSON.parse(readFileSync(new URL('../../evaluations/fixtures/cs-notes-v1.json', import.meta.url), 'utf8'));
const readReport = (name) => JSON.parse(readFileSync(new URL(`../../evaluations/reports/${name}.json`, import.meta.url), 'utf8'));
const input = {
  source_snapshot_id: 'snapshot-1', settings_version: 1, allow_ai_explanations: false,
  profile: { depth: 'detailed', format: 'topic_outline' },
  sources: [{ id: 'source-v1', text: 'The array must be sorted.', start_ms: 0, end_ms: 1000 }],
};
const validNotes = () => ({
  schema_version: 1, source_snapshot_id: 'snapshot-1', settings_version: 1,
  blocks: [{ id: 'b1', topic: 'Precondition', kind: 'qualification', passages: [{
    id: 'p1', evidence_kind: 'lecture_paraphrase', text: 'Use a sorted array.',
    sources: [{ source_id: 'source-v1', quote: 'The array must be sorted.', occurrence: 0 }],
  }] }], issues: [], coverage: [{ source_id: 'source-v1', disposition: 'used', reason: 'Precondition retained.' }],
});
const speech = () => ({
  schema_version: 1, run_id: 'run-A', window_id: 'window-1', sample_rate: 48000,
  window_start_sample: 0, window_end_sample: 96000, outcome: 'speech',
  segments: [{ id: 'segment-A', start_sample: 0, end_sample: 48000, text: 'Sorted array.', stability: 'provisional', confidence: { kind: 'unavailable', value: null } }],
});

test('development fixtures have valid source intervals and rubric references', () => {
  assert.equal(validateFixtureSet(dataset), true);
  assert.equal(dataset.cases.length, 3);
});
test('fixture validation rejects duplicated IDs and references to absent evidence', () => {
  const duplicate = structuredClone(dataset);
  duplicate.cases.push(duplicate.cases[0]);
  assert.throws(() => validateFixtureSet(duplicate), /fixture ID/);
  const unknown = structuredClone(dataset);
  unknown.cases[0].rubric.key_points[0].source_ids = ['not-present'];
  assert.throws(() => validateFixtureSet(unknown), /unknown source/);
});
test('note contracts resolve source versions but make no semantic-support claim', () => {
  const result = validateNotes(validNotes(), input);
  assert.equal(result.structurallyValid, true);
  assert.equal(result.semanticSupport, 'not_evaluated');
  assert.deepEqual(result.resolvedCitations[0], { passage_id: 'p1', source_id: 'source-v1', start: 0, end: 25 });
});
test('unknown fields cannot impersonate approval or student edits', () => {
  const notes = validNotes();
  notes.approved = true;
  assert.throws(() => validateNotes(notes, input), /schema/);
  delete notes.approved;
  notes.blocks[0].passages[0].evidence_kind = 'student_addition';
  assert.throws(() => validateNotes(notes, input), /schema/);
});
test('provider grammar adaptation keeps structural rules while server validation retains size limits', () => {
  assert.equal(providerNoteSchema.additionalProperties, false);
  assert.ok(!JSON.stringify(providerNoteSchema).includes('"$ref"'));
  assert.ok(!JSON.stringify(providerNoteSchema).includes('"maxLength"'));
  const notes = validNotes();
  notes.blocks[0].topic = 'x'.repeat(201);
  assert.throws(() => validateNotes(notes, input), /schema/);
});
test('stale source or settings snapshots are rejected', () => {
  for (const override of [{ source_snapshot_id: 'old' }, { settings_version: 2 }]) {
    assert.throws(() => validateNotes({ ...validNotes(), ...override }, input), /Stale/);
  }
});
test('unknown citations and invented quotes are rejected', () => {
  for (const override of [{ source_id: 'unknown' }, { quote: 'This was never said.' }, { occurrence: 1 }]) {
    const notes = validNotes();
    Object.assign(notes.blocks[0].passages[0].sources[0], override);
    assert.throws(() => validateNotes(notes, input), /citation|Citation/);
  }
});
test('an exact quote must match its cited text verbatim', () => {
  const notes = validNotes();
  notes.blocks[0].passages[0].evidence_kind = 'exact_quote';
  assert.throws(() => validateNotes(notes, input), /verbatim/);
  notes.blocks[0].passages[0].text = input.sources[0].text;
  assert.equal(validateNotes(notes, input).structurallyValid, true);
});
test('Unicode source spans use code points and handle repeated quoted text', () => {
  const source = { id: 'unicode', text: '🌳 term; term' };
  assert.deepEqual(resolveCitation(source, { source_id: 'unicode', quote: 'term', occurrence: 1 }), { start: 8, end: 12 });
});
test('duplicate block and passage IDs cannot silently replace prior output', () => {
  const notes = validNotes();
  notes.blocks.push(structuredClone(notes.blocks[0]));
  assert.throws(() => validateNotes(notes, input), /Duplicate block/);
  notes.blocks[1].id = 'b2';
  assert.throws(() => validateNotes(notes, input), /duplicate passage/);
});
test('lecture passages require citations', () => {
  const notes = validNotes();
  notes.blocks[0].passages[0].sources = [];
  assert.throws(() => validateNotes(notes, input), /lacks evidence/);
});
test('AI explanations require opt-in and cannot borrow lecture attribution', () => {
  const notes = validNotes();
  notes.blocks[0].passages.push({ id: 'ai1', text: 'An analogy.', evidence_kind: 'ai_explanation', sources: [] });
  assert.throws(() => validateNotes(notes, input), /disabled/);
  assert.equal(validateNotes(notes, { ...input, allow_ai_explanations: true }).structurallyValid, true);
  notes.blocks[0].passages[1].sources = notes.blocks[0].passages[0].sources;
  assert.throws(() => validateNotes(notes, { ...input, allow_ai_explanations: true }), /attributed/);
});
test('every input source must be accounted for without duplicate ledger entries', () => {
  const notes = validNotes();
  notes.coverage = [];
  assert.throws(() => validateNotes(notes, input), /Missing source coverage/);
  notes.coverage = [validNotes().coverage[0], validNotes().coverage[0]];
  assert.throws(() => validateNotes(notes, input), /coverage ledger/);
});
test('uncited evidence cannot be declared used and cited evidence cannot be hidden as omitted', () => {
  const notes = validNotes();
  notes.coverage[0].disposition = 'omitted';
  assert.throws(() => validateNotes(notes, input), /mismatch/);
});
test('source issues must refer to available input evidence', () => {
  const notes = validNotes();
  notes.issues.push({ code: 'missing_visual', detail: 'Board unavailable.', source_ids: ['absent'] });
  assert.throws(() => validateNotes(notes, input), /unknown source/);
});
test('an empty evidence set cannot yield fabricated notes or silent empty success', () => {
  const notes = validNotes();
  const emptyInput = { ...input, sources: [] };
  notes.blocks = [];
  notes.coverage = [];
  assert.throws(() => validateNotes(notes, emptyInput), /disclose missing evidence/);
  notes.issues = [{ code: 'incomplete_evidence', detail: 'No usable source.', source_ids: [] }];
  assert.equal(validateNotes(notes, emptyInput).structurallyValid, true);
});
test('structural validation deliberately cannot detect a semantically false paraphrase', () => {
  const notes = validNotes();
  notes.blocks[0].passages[0].text = 'The array must be unsorted.';
  assert.equal(validateNotes(notes, input).semanticSupport, 'not_evaluated');
});
test('prompt construction excludes answer keys and keeps attack strings inside evidence', () => {
  const original = dataset.cases[2].input;
  const request = buildNoteRequest({ ...original, rubric: 'SECRET_ANSWER_KEY', human_approved: true }, 'Trusted instructions');
  assert.equal(request.length, 2);
  assert.equal(request[0].role, 'system');
  assert.equal(request[1].role, 'user');
  assert.ok(request[1].content.includes('PWNED'));
  assert.ok(!JSON.stringify(request).includes('SECRET_ANSWER_KEY'));
  assert.ok(!request[0].content.includes('PWNED'));
});
test('speech output permits explicit uncalibrated scores without treating them as probabilities', () => {
  const result = speech();
  assert.equal(validateSpeech(result), true);
  result.segments[0].confidence = { kind: 'uncalibrated_score', value: -0.4 };
  assert.equal(validateSpeech(result), true);
});
test('speech windows reject reversed, overlapping, and out-of-range segments', () => {
  for (const override of [{ start_sample: 50000, end_sample: 48000 }, { end_sample: 100000 }]) {
    const result = speech();
    Object.assign(result.segments[0], override);
    assert.throws(() => validateSpeech(result), /outside window/);
  }
  const overlap = speech();
  overlap.segments.push({ ...overlap.segments[0], id: 'B', start_sample: 20000 });
  assert.throws(() => validateSpeech(overlap), /out of order/);
});
test('silence cannot contain hallucinated speech', () => {
  assert.throws(() => validateSpeech({ ...speech(), outcome: 'silence' }), /Silence/);
  assert.equal(validateSpeech({ ...speech(), outcome: 'silence', segments: [] }), true);
});
test('word error rate detects dropped negation and does not treat empty reference as perfect', () => {
  assert.deepEqual(wordErrorRate('not sorted', 'sorted'), { edits: 1, referenceWords: 2, hypothesisWords: 1, wer: 0.5 });
  assert.equal(wordErrorRate('sorted array', 'Sorted, array!').wer, 0);
  assert.equal(wordErrorRate('', 'hallucinated words').wer, null);
  assert.equal(wordErrorRate('', 'hallucinated words').edits, 2);
});
test('assistant review cannot become human approval or release qualification', () => {
  const rubric = dataset.cases[0].rubric;
  const review = { reviewer_kind: 'assistant', coverage: rubric.key_points.map(({ id }) => ({ id, covered: true })), claims_reviewed: 10, claims_supported: 10, critical_errors: 0 };
  const result = reviewSummary(rubric, review);
  assert.equal(result.thresholdsMet, true);
  assert.equal(result.status, 'human_review_required');
  assert.equal(result.releaseEligible, false);
});
test('missing critical content fails fixture thresholds and incomplete reviews are rejected', () => {
  const rubric = dataset.cases[1].rubric;
  const review = { reviewer_kind: 'human', coverage: rubric.key_points.map(({ id }) => ({ id, covered: false })), claims_reviewed: 3, claims_supported: 3, critical_errors: 0 };
  assert.equal(reviewSummary(rubric, review).status, 'fixture_thresholds_failed');
  review.coverage.pop();
  assert.throws(() => reviewSummary(rubric, review), /Incomplete review/);
});
test('review counts cannot fabricate support or a passing zero-claim score', () => {
  const rubric = dataset.cases[1].rubric;
  const review = { reviewer_kind: 'human', coverage: rubric.key_points.map(({ id }) => ({ id, covered: true })), claims_reviewed: 0, claims_supported: 0, critical_errors: 0 };
  assert.equal(reviewSummary(rubric, review).thresholdsMet, false);
  review.claims_supported = 1;
  assert.throws(() => reviewSummary(rubric, review), /exceed/);
});

test('promoted trials remain bound to the recorded evidence, prompts, and schemas', () => {
  const hash = (text) => createHash('sha256').update(text).digest('hex');
  const textHash = (relative) => hash(readFileSync(new URL(relative, import.meta.url), 'utf8').replace(/\r\n/g, '\n'));
  for (const [name, version] of [['qwen3-4b-full-schema-failure', 'v1'], ['qwen3-4b-v1-synthetic', 'v1'], ['qwen3-4b-v2-correction', 'v2']]) {
    const report = readReport(name);
    assert.equal(report.dataset_sha256, textHash('../../evaluations/fixtures/cs-notes-v1.json'));
    assert.equal(report.prompt_sha256, textHash(`../../prompts/note-generation-${version}.txt`));
    assert.equal(report.schema_sha256, hash(JSON.stringify(noteSchema)));
    if (report.provider_schema_sha256) assert.equal(report.provider_schema_sha256, hash(JSON.stringify(providerNoteSchema)));
    assert.equal(report.human_review_status, 'pending');
    assert.equal(report.release_eligible, false);
  }
});

test('real v1 outputs preserve two structural successes and reject the observed coverage mismatch', () => {
  const report = readReport('qwen3-4b-v1-synthetic');
  assert.equal(report.cases.length, 3);
  assert.equal(report.contract_valid_cases, 2);
  for (const result of report.cases) {
    const fixture = dataset.cases.find(({ id }) => id === result.id);
    assert.ok(fixture);
    if (result.contract_valid) assert.equal(validateNotes(result.output, fixture.input).structurallyValid, true);
    else {
      assert.equal(result.id, 'quoted-instruction-and-ambiguity');
      assert.throws(() => validateNotes(result.output, fixture.input), /Coverage use\/citation mismatch/);
    }
  }
});

test('trial history retains grammar failures and the limited v2 evaluation scope', () => {
  const failed = readReport('qwen3-4b-full-schema-failure');
  assert.equal(failed.cases.length, 3);
  for (const result of failed.cases) {
    assert.equal(result.contract_valid, false);
    assert.match(result.error, /HTTP 400/);
    assert.equal(result.output, undefined);
  }
  const followup = readReport('qwen3-4b-v2-correction');
  assert.deepEqual(followup.selected_case_ids, ['correction-and-conditions']);
  assert.equal(followup.cases.length, 1);
  const fixture = dataset.cases.find(({ id }) => id === followup.cases[0].id);
  assert.equal(validateNotes(followup.cases[0].output, fixture.input).structurallyValid, true);
});
