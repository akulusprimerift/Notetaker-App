import { readFileSync } from 'node:fs';
import Ajv2020 from 'ajv/dist/2020.js';

const readJson = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
export const noteSchema = readJson('../../contracts/ai/note-output.schema.json');
export const speechSchema = readJson('../../contracts/ai/speech-result.schema.json');
const ajv = new Ajv2020({ allErrors: true, strict: true });
const noteShape = ajv.compile(noteSchema);
const speechShape = ajv.compile(speechSchema);
const fail = (message) => { throw new Error(message); };

// Ollama grammar limits are not identical to JSON Schema validation limits.
// Inline local references and leave size/range enforcement to the canonical Ajv validator.
function providerSchema(node, root) {
  if (Array.isArray(node)) return node.map((item) => providerSchema(item, root));
  if (!node || typeof node !== 'object') return node;
  if (node.$ref) {
    if (!node.$ref.startsWith('#/$defs/')) fail('Unsupported provider schema reference');
    return providerSchema(root.$defs[node.$ref.slice('#/$defs/'.length)], root);
  }
  const omitted = new Set(['$schema', '$id', '$defs', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minimum', 'maximum', 'uniqueItems']);
  return Object.fromEntries(Object.entries(node).filter(([key]) => !omitted.has(key)).map(([key, value]) => [key, providerSchema(value, root)]));
}
export const providerNoteSchema = providerSchema(noteSchema, noteSchema);

export function validateFixtureSet(dataset) {
  if (dataset.origin !== 'synthetic' || dataset.audio_available !== false) fail('Only synthetic text fixtures are enabled in this harness');
  if (!Array.isArray(dataset.cases) || dataset.cases.length === 0) fail('Missing fixture cases');
  const caseIds = new Set();
  for (const entry of dataset.cases) {
    if (!entry.id || caseIds.has(entry.id)) fail('Duplicate or missing fixture ID');
    caseIds.add(entry.id);
    const ids = new Set();
    for (const source of entry.input.sources) {
      if (!source.id || ids.has(source.id) || typeof source.text !== 'string' || !source.text.trim()) fail('Invalid fixture source');
      if (!Number.isSafeInteger(source.start_ms) || source.start_ms < 0 || source.end_ms <= source.start_ms) fail('Invalid fixture source interval');
      ids.add(source.id);
    }
    const points = new Set();
    for (const point of entry.rubric.key_points) {
      if (!point.id || points.has(point.id) || typeof point.critical !== 'boolean' || !point.description) fail('Invalid rubric item');
      points.add(point.id);
      if (!point.source_ids.length || point.source_ids.some((id) => !ids.has(id))) fail('Rubric cites unknown source');
    }
    if (!points.size) fail('Empty rubric');
  }
  return true;
}

export function resolveCitation(source, citation) {
  if (!source || source.id !== citation.source_id) fail('Unknown citation source');
  let offset = -1;
  for (let index = 0; index <= citation.occurrence; index++) {
    offset = source.text.indexOf(citation.quote, offset + 1);
    if (offset < 0) fail('Citation quote/occurrence does not resolve');
  }
  // Persist Unicode code-point offsets, not JavaScript UTF-16 code-unit offsets.
  return { start: [...source.text.slice(0, offset)].length, end: [...source.text.slice(0, offset + citation.quote.length)].length };
}

export function validateNotes(output, input) {
  if (!noteShape(output)) fail(`Invalid note schema: ${ajv.errorsText(noteShape.errors)}`);
  if (output.source_snapshot_id !== input.source_snapshot_id || output.settings_version !== input.settings_version) fail('Stale source/settings metadata');
  const sources = new Map(input.sources.map((source) => [source.id, source]));
  const blockIds = new Set();
  const passageIds = new Set();
  const citedIds = new Set();
  const resolved = [];
  for (const block of output.blocks) {
    if (blockIds.has(block.id)) fail('Duplicate block ID');
    blockIds.add(block.id);
    for (const passage of block.passages) {
      if (!passage.text.trim() || passageIds.has(passage.id)) fail('Empty passage or duplicate passage ID');
      passageIds.add(passage.id);
      if (['lecture_paraphrase', 'exact_quote'].includes(passage.evidence_kind) && !passage.sources.length) fail('Lecture passage lacks evidence');
      if (passage.evidence_kind === 'ai_explanation' && (!input.allow_ai_explanations || passage.sources.length)) fail('AI explanation disabled or falsely lecture-attributed');
      for (const citation of passage.sources) {
        const span = resolveCitation(sources.get(citation.source_id), citation);
        citedIds.add(citation.source_id);
        resolved.push({ passage_id: passage.id, source_id: citation.source_id, ...span });
      }
      if (passage.evidence_kind === 'exact_quote' && (passage.sources.length !== 1 || passage.text !== passage.sources[0].quote)) fail('Exact quote is not verbatim');
    }
  }
  const coveredIds = new Set();
  for (const item of output.coverage) {
    if (!sources.has(item.source_id) || coveredIds.has(item.source_id) || !item.reason.trim()) fail('Invalid coverage ledger');
    coveredIds.add(item.source_id);
    if ((item.disposition === 'used') !== citedIds.has(item.source_id)) fail('Coverage use/citation mismatch');
  }
  if (coveredIds.size !== sources.size) fail('Missing source coverage entries');
  for (const issue of output.issues) {
    if (issue.source_ids.some((id) => !sources.has(id))) fail('Issue references unknown source');
    if (issue.code !== 'incomplete_evidence' && !issue.source_ids.length) fail('Source issue lacks a source');
  }
  if (!sources.size && output.blocks.length) fail('Notes invented without source evidence');
  if (!output.blocks.length && !output.issues.length) fail('Empty notes must disclose missing evidence');
  return { structurallyValid: true, resolvedCitations: resolved, semanticSupport: 'not_evaluated' };
}

export function validateSpeech(output) {
  if (!speechShape(output)) fail(`Invalid speech schema: ${ajv.errorsText(speechShape.errors)}`);
  if (output.window_end_sample <= output.window_start_sample) fail('Invalid speech window');
  if (output.outcome === 'silence' && output.segments.length) fail('Silence cannot contain invented speech');
  if (output.outcome === 'speech' && !output.segments.length) fail('Speech outcome needs segments');
  let end = output.window_start_sample;
  const ids = new Set();
  for (const segment of output.segments) {
    if (ids.has(segment.id) || !segment.text.trim()) fail('Invalid speech segment');
    ids.add(segment.id);
    if (segment.start_sample < end || segment.end_sample <= segment.start_sample || segment.end_sample > output.window_end_sample) fail('Speech segment outside window or out of order');
    if ((segment.confidence.kind === 'unavailable') !== (segment.confidence.value === null)) fail('Invalid confidence representation');
    end = segment.end_sample;
  }
  return true;
}

export function buildNoteRequest(input, prompt) {
  // Explicit allowlist: evaluation rubrics/review labels never enter the model input.
  const evidence = {
    source_snapshot_id: input.source_snapshot_id, settings_version: input.settings_version,
    allow_ai_explanations: input.allow_ai_explanations, profile: input.profile,
    sources: input.sources.map(({ id, text, start_ms, end_ms }) => ({ id, text, start_ms, end_ms })),
  };
  return [
    { role: 'system', content: `${prompt}\nOUTPUT_SCHEMA:\n${JSON.stringify(noteSchema)}` },
    { role: 'user', content: `LECTURE_EVIDENCE_JSON:\n${JSON.stringify(evidence)}` },
  ];
}

export function wordErrorRate(reference, hypothesis) {
  const words = (text) => text.normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? [];
  const expected = words(reference);
  const actual = words(hypothesis);
  let previous = Array.from({ length: actual.length + 1 }, (_, index) => index);
  expected.forEach((word, row) => {
    const next = [row + 1];
    actual.forEach((other, column) => {
      next.push(Math.min(previous[column + 1] + 1, next[column] + 1, previous[column] + (word === other ? 0 : 1)));
    });
    previous = next;
  });
  const edits = previous[actual.length];
  return { edits, referenceWords: expected.length, hypothesisWords: actual.length, wer: expected.length ? edits / expected.length : null };
}

export function reviewSummary(rubric, review) {
  if (!['human', 'assistant'].includes(review.reviewer_kind)) fail('Unknown reviewer kind');
  const expected = new Map(rubric.key_points.map((point) => [point.id, point]));
  const seen = new Set();
  let covered = 0;
  let criticalMissing = 0;
  for (const item of review.coverage) {
    if (!expected.has(item.id) || seen.has(item.id) || typeof item.covered !== 'boolean') fail('Invalid review coverage');
    seen.add(item.id);
    if (item.covered) covered++;
    else if (expected.get(item.id).critical) criticalMissing++;
  }
  if (seen.size !== expected.size) fail('Incomplete review coverage');
  for (const field of ['claims_reviewed', 'claims_supported', 'critical_errors']) {
    if (!Number.isSafeInteger(review[field]) || review[field] < 0) fail('Invalid review count');
  }
  if (review.claims_supported > review.claims_reviewed) fail('Supported claims exceed reviewed claims');
  const coverage = covered / expected.size;
  const citationSupport = review.claims_reviewed ? review.claims_supported / review.claims_reviewed : null;
  const thresholdsMet = coverage >= 0.9 && criticalMissing === 0 && citationSupport !== null && citationSupport >= 0.95 && review.critical_errors === 0;
  return { coverage, criticalMissing, citationSupport, thresholdsMet, reviewerKind: review.reviewer_kind,
    status: review.reviewer_kind === 'human' ? (thresholdsMet ? 'fixture_thresholds_met' : 'fixture_thresholds_failed') : 'human_review_required',
    releaseEligible: false };
}
