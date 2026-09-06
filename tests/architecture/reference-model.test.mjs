import test from 'node:test';
import assert from 'node:assert/strict';
import {
  mayAcknowledge, receiveChunk, savedThrough, finalizationDecision,
  publicationDecision, consumeEvent, claimJob, updateDecision,
} from './reference-model.mjs';

const chunk = (sequence, overrides = {}) => ({
  runId: 'run-A', sequence, startSample: sequence * 96000, sampleCount: 96000,
  sampleRate: 48000, encoding: 'pcm_s16le_wav', byteLength: 192044,
  checksum: `hash-${sequence}`, verified: true, ...overrides,
});
const fullManifest = {
  sealed: true, lastSequence: 2, verifiedSequences: [0, 1, 2],
};
const current = {
  lifecycle: 'active', lifecycleEpoch: 1, audioEpoch: 1,
  attemptToken: 'attempt-A', sourceRevision: 4, settingsVersion: 2, documentVersion: 7,
};

test('acknowledgement requires verified objects and the complete durable transaction', () => {
  for (const objectVerified of [false, true]) {
    for (const metadataCommitted of [false, true]) {
      for (const jobAndOutboxCommitted of [false, true]) {
        assert.equal(mayAcknowledge({ objectVerified, metadataCommitted, jobAndOutboxCommitted }),
          objectVerified && metadataCommitted && jobAndOutboxCommitted);
      }
    }
  }
  assert.equal(mayAcknowledge({}), false);
});

test('out-of-order verified audio never advances coverage across a missing chunk', () => {
  let chunks = receiveChunk(new Map(), chunk(2));
  assert.deepEqual(savedThrough(chunks, 'run-A'), { nextSequence: 0, endSample: 0 });
  chunks = receiveChunk(chunks, chunk(0));
  assert.deepEqual(savedThrough(chunks, 'run-A'), { nextSequence: 1, endSample: 96000 });
  chunks = receiveChunk(chunks, chunk(1));
  assert.deepEqual(savedThrough(chunks, 'run-A'), { nextSequence: 3, endSample: 288000 });
});

test('all arrival permutations produce the same contiguous saved coverage', () => {
  for (const order of [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]]) {
    const chunks = order.reduce((state, sequence) => receiveChunk(state, chunk(sequence)), new Map());
    assert.equal(savedThrough(chunks, 'run-A').endSample, 288000);
  }
});

test('identical chunk retries are idempotent and preserve the original model state', () => {
  const original = receiveChunk(new Map(), chunk(0));
  const retried = receiveChunk(original, chunk(0));
  assert.equal(retried.size, 1);
  assert.equal(original.size, 1);
  assert.notEqual(original, retried);
});

test('same chunk identity cannot be reused for different content or timing', () => {
  const original = receiveChunk(new Map(), chunk(0));
  for (const changed of [{ checksum: 'different' }, { sampleCount: 48000 }, { sampleRate: 16000 }]) {
    assert.throws(() => receiveChunk(original, chunk(0, changed)), /identity conflict/);
  }
});

test('sample gaps, unverified chunks, and other runs never inflate saved coverage', () => {
  for (const changed of [{ startSample: 96001 }, { verified: false }, { runId: 'run-B' }]) {
    let chunks = receiveChunk(new Map(), chunk(0));
    chunks = receiveChunk(chunks, chunk(1, changed));
    assert.equal(savedThrough(chunks, 'run-A').endSample, 96000);
  }
});

test('chunk identity rejects invalid sequence and empty audio', () => {
  assert.throws(() => receiveChunk(new Map(), chunk(-1)), /invalid sequence/);
  assert.throws(() => receiveChunk(new Map(), chunk(0, { sampleCount: 0 })), /empty chunk/);
});

test('stop without a sealed manifest is not permission to finalize', () => {
  assert.equal(finalizationDecision({ ...fullManifest, sealed: false }), 'waiting_for_seal');
});

test('missing audio needs an explicit incomplete-evidence decision', () => {
  const partial = { ...fullManifest, verifiedSequences: [0, 2] };
  assert.equal(finalizationDecision(partial), 'waiting_for_evidence_decision');
  assert.equal(finalizationDecision({ ...partial, allowIncomplete: true }), 'ready_incomplete');
});

test('a timeline gap remains incomplete even with every declared chunk present', () => {
  assert.equal(finalizationDecision({ ...fullManifest, knownGap: true }), 'waiting_for_evidence_decision');
  assert.equal(finalizationDecision({ ...fullManifest, knownGap: true, allowIncomplete: true }), 'ready_incomplete');
});

test('late recovery creates readiness for a new snapshot without changing the old input', () => {
  const old = { ...fullManifest, verifiedSequences: [0, 2], allowIncomplete: true };
  assert.equal(finalizationDecision(old), 'ready_incomplete');
  assert.equal(finalizationDecision({ ...old, verifiedSequences: [0, 1, 2] }), 'ready');
  assert.deepEqual(old.verifiedSequences, [0, 2]);
});

test('empty or unusable evidence cannot produce ready notes', () => {
  assert.equal(finalizationDecision({ sealed: true, lastSequence: -1, verifiedSequences: [] }), 'no_usable_evidence');
  assert.equal(finalizationDecision({ ...fullManifest, usableTranscript: false }), 'no_usable_evidence');
  assert.equal(finalizationDecision({ ...fullManifest, verifiedSequences: [], allowIncomplete: true }), 'no_usable_evidence');
});

test('audio readiness does not imply transcription has completed', () => {
  assert.equal(finalizationDecision({ ...fullManifest, transcriptionTerminal: false }), 'waiting_for_transcription');
});

test('out-of-manifest chunks are conflicts, not silent extensions of a sealed run', () => {
  assert.throws(() => finalizationDecision({ ...fullManifest, verifiedSequences: [0, 1, 2, 3] }), /manifest conflict/);
  assert.equal(finalizationDecision({ ...fullManifest, verifiedSequences: [0, 1, 1, 2] }), 'ready');
});

test('current generation can publish only when the block is not student protected', () => {
  assert.equal(publicationDecision(current, current), 'publish');
  assert.equal(publicationDecision(current, current, { humanProtected: true }), 'proposal_required');
});

test('every changed generation base independently rejects stale publication', () => {
  for (const field of ['lifecycleEpoch', 'attemptToken', 'sourceRevision', 'settingsVersion', 'documentVersion']) {
    assert.equal(publicationDecision(current, { ...current, [field]: 'stale' }), 'rejected_stale', field);
  }
  assert.equal(publicationDecision(current, {}), 'rejected_stale');
});

test('a deletion or tombstone wins over a previously valid worker result', () => {
  for (const lifecycle of ['deleting', 'deleted']) {
    assert.equal(publicationDecision({ ...current, lifecycle }, current), 'rejected_lifecycle');
  }
});

test('audio removal fences audio work without blocking transcript-only note work', () => {
  const afterRemoval = { ...current, audioEpoch: 2 };
  assert.equal(publicationDecision(afterRemoval, current, { audioDependent: true }), 'rejected_stale');
  assert.equal(publicationDecision(afterRemoval, current), 'publish');
});

test('event deduplication is per consumer, not global across legitimate consumers', () => {
  const first = consumeEvent(new Set(), 'speech', 'event-A');
  const repeated = consumeEvent(first.inbox, 'speech', 'event-A');
  const independent = consumeEvent(repeated.inbox, 'diagnostics', 'event-A');
  assert.equal(first.applied, true);
  assert.equal(repeated.applied, false);
  assert.equal(independent.applied, true);
  assert.equal(independent.inbox.size, 2);
});

test('UI replay ignores duplicates and detects gaps before applying later updates', () => {
  assert.equal(updateDecision(7, 7), 'ignore_duplicate');
  assert.equal(updateDecision(7, 3), 'ignore_duplicate');
  assert.equal(updateDecision(7, 8), 'apply');
  assert.equal(updateDecision(7, 9), 'request_replay');
  assert.throws(() => updateDecision(-1, 0), /invalid current cursor/);
});

test('notification and reconciler claims share the same logical job lease', () => {
  const first = claimJob({ status: 'pending', logicalKey: 'speech:manifest-1' }, { now: 0, leaseMs: 100, attemptToken: 'A' });
  const duplicate = claimJob(first.job, { now: 50, leaseMs: 100, attemptToken: 'B' });
  assert.equal(first.claimed, true);
  assert.equal(duplicate.claimed, false);
  assert.equal(duplicate.job.attemptToken, 'A');
});

test('expired job leases create a new attempt and fence the previous output', () => {
  const original = claimJob({ status: 'pending' }, { now: 0, leaseMs: 100, attemptToken: 'A' });
  const recovered = claimJob(original.job, { now: 100, leaseMs: 100, attemptToken: 'B' });
  assert.equal(recovered.claimed, true);
  assert.equal(recovered.job.leaseExpiresAt, 200);
  assert.equal(publicationDecision({ ...current, attemptToken: recovered.job.attemptToken },
    { ...current, attemptToken: original.job.attemptToken }), 'rejected_stale');
});

test('completed and cancelled jobs cannot be reopened by duplicate notifications', () => {
  for (const status of ['completed', 'cancelled']) {
    const result = claimJob({ status, attemptToken: 'A' }, { now: 1000, leaseMs: 100, attemptToken: 'B' });
    assert.equal(result.claimed, false);
    assert.equal(result.job.status, status);
  }
});

test('reclaiming an expired attempt must not reuse its publication token', () => {
  const job = { status: 'running', attemptToken: 'A', leaseExpiresAt: 100 };
  assert.throws(() => claimJob(job, { now: 100, leaseMs: 100, attemptToken: 'A' }), /token must change/);
});
