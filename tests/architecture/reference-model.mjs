// Executable design model only. No browser, database, broker, or storage adapter.
// Production transactions must enforce these decisions atomically; this model cannot prove that.

function nonnegativeInteger(value, name) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`invalid ${name}`);
}

export function mayAcknowledge({ objectVerified, metadataCommitted, jobAndOutboxCommitted }) {
  return objectVerified === true && metadataCommitted === true && jobAndOutboxCommitted === true;
}

export function receiveChunk(chunks, chunk) {
  if (!chunk.runId || !chunk.checksum) throw new Error('missing chunk identity');
  nonnegativeInteger(chunk.sequence, 'sequence');
  nonnegativeInteger(chunk.startSample, 'startSample');
  nonnegativeInteger(chunk.sampleCount, 'sampleCount');
  if (chunk.sampleCount === 0) throw new Error('empty chunk');
  const key = JSON.stringify([chunk.runId, chunk.sequence]);
  const existing = chunks.get(key);
  const fields = ['checksum', 'startSample', 'sampleCount', 'sampleRate', 'encoding', 'byteLength'];
  if (existing && fields.some((field) => existing[field] !== chunk[field])) {
    throw new Error('chunk identity conflict');
  }
  const next = new Map(chunks);
  if (!existing) next.set(key, Object.freeze({ ...chunk }));
  return next;
}

export function savedThrough(chunks, runId) {
  const ordered = [...chunks.values()].filter((chunk) => chunk.runId === runId)
    .sort((left, right) => left.sequence - right.sequence);
  let nextSequence = 0;
  let nextSample = 0;
  for (const chunk of ordered) {
    if (chunk.sequence !== nextSequence || chunk.startSample !== nextSample || chunk.verified !== true) break;
    nextSequence++;
    nextSample += chunk.sampleCount;
  }
  return { nextSequence, endSample: nextSample };
}

export function finalizationDecision({
  sealed, lastSequence, verifiedSequences, knownGap = false,
  allowIncomplete = false, transcriptionTerminal = true, usableTranscript = true,
}) {
  if (!sealed) return 'waiting_for_seal';
  if (!Number.isSafeInteger(lastSequence) || lastSequence < -1 || lastSequence > 100000) {
    throw new Error('invalid manifest bound');
  }
  const received = new Set(verifiedSequences);
  for (const sequence of received) {
    nonnegativeInteger(sequence, 'verified sequence');
    if (sequence > lastSequence) throw new Error('manifest conflict');
  }
  if (lastSequence === -1) return 'no_usable_evidence';
  const incomplete = knownGap || received.size !== lastSequence + 1;
  if (incomplete && !allowIncomplete) return 'waiting_for_evidence_decision';
  if (!transcriptionTerminal) return 'waiting_for_transcription';
  if (received.size === 0 || !usableTranscript) return 'no_usable_evidence';
  return incomplete ? 'ready_incomplete' : 'ready';
}

export function publicationDecision(current, expected, { humanProtected = false, audioDependent = false } = {}) {
  if (current.lifecycle !== 'active') return 'rejected_lifecycle';
  const bases = ['lifecycleEpoch', 'attemptToken', 'sourceRevision', 'settingsVersion', 'documentVersion'];
  if (audioDependent) bases.push('audioEpoch');
  if (bases.some((field) => expected[field] === undefined || current[field] !== expected[field])) {
    return 'rejected_stale';
  }
  return humanProtected ? 'proposal_required' : 'publish';
}

export function consumeEvent(inbox, consumerName, eventId) {
  if (!consumerName || !eventId) throw new Error('missing consumer/event identity');
  const key = JSON.stringify([consumerName, eventId]);
  const next = new Set(inbox);
  const applied = !next.has(key);
  next.add(key);
  return { inbox: next, applied };
}

export function claimJob(job, { now, leaseMs, attemptToken }) {
  nonnegativeInteger(now, 'claim time');
  nonnegativeInteger(leaseMs, 'lease duration');
  if (!attemptToken || leaseMs === 0) throw new Error('invalid job claim');
  if (job.status === 'completed' || job.status === 'cancelled') return { claimed: false, job };
  if (job.status === 'running' && job.leaseExpiresAt > now) return { claimed: false, job };
  if (job.status !== 'pending' && job.status !== 'running') return { claimed: false, job };
  if (job.attemptToken === attemptToken) throw new Error('attempt token must change');
  return { claimed: true, job: { ...job, status: 'running', attemptToken, leaseExpiresAt: now + leaseMs } };
}

export function updateDecision(currentCursor, incomingCursor) {
  nonnegativeInteger(currentCursor, 'current cursor');
  nonnegativeInteger(incomingCursor, 'incoming cursor');
  if (incomingCursor <= currentCursor) return 'ignore_duplicate';
  if (incomingCursor !== currentCursor + 1) return 'request_replay';
  return 'apply';
}
