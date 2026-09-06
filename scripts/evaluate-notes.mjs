import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildNoteRequest, noteSchema, providerNoteSchema, validateFixtureSet, validateNotes } from '../evaluations/lib/contracts.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const args = process.argv.slice(2);
if (args.length < 1 || args.length > 3 || !['qwen3:4b', 'qwen3:8b'].includes(args[0]) || (args[2] && !['v1', 'v2'].includes(args[2]))) {
  console.error('Usage: npm run eval:notes -- qwen3:4b [case-id|all] [v1|v2]');
  process.exit(2);
}
const model = args[0];
const base = 'http://127.0.0.1:11434';
// Normalize checkout line endings so fixture/prompt hashes survive Windows Git checkouts.
const readText = async (relative) => (await readFile(path.join(root, relative), 'utf8')).replace(/\r\n/g, '\n');
const datasetText = await readText('evaluations/fixtures/cs-notes-v1.json');
const dataset = JSON.parse(datasetText);
validateFixtureSet(dataset);
const cases = !args[1] || args[1] === 'all' ? dataset.cases : dataset.cases.filter((entry) => entry.id === args[1]);
if (!cases.length) { console.error('Unknown fixture case'); process.exit(2); }
const promptVersion = args[2] ?? 'v1';
const prompt = await readText(`prompts/note-generation-${promptVersion}.txt`);
const hash = (text) => createHash('sha256').update(text).digest('hex');
const startedAt = new Date().toISOString();
const directory = path.join(root, 'evaluations/local-runs', startedAt.replace(/[:.]/g, '-'));
await mkdir(directory, { recursive: true });
const report = {
  started_at: startedAt, dataset_version: dataset.dataset_version, dataset_sha256: hash(datasetText),
  prompt_sha256: hash(prompt), schema_sha256: hash(JSON.stringify(noteSchema)),
  provider_schema_sha256: hash(JSON.stringify(providerNoteSchema)),
  fixture_origin: dataset.origin, human_review_status: 'pending', model, model_digest: null,
  prompt_version: promptVersion, selected_case_ids: cases.map((entry) => entry.id),
  environment: { node: process.version, cpu: os.cpus()[0]?.model, logical_processors: os.cpus().length, memory_bytes: os.totalmem(), platform: os.platform(), os_release: os.release() },
  settings: { temperature: 0, seed: 42, num_ctx: 8192, num_predict: 4096 },
  cases: [], release_eligible: false,
};
const save = () => writeFile(path.join(directory, 'report.json'), JSON.stringify(report, null, 2) + '\n');
async function request(route, body, timeout = 10000) {
  const response = await fetch(`${base}/api/${route}`, {
    method: body ? 'POST' : 'GET', redirect: 'error',
    headers: body ? { 'content-type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) throw new Error(`Ollama ${route}: HTTP ${response.status}`);
  const result = await response.json();
  if (result.error) throw new Error(`Ollama ${route}: ${result.error}`);
  return result;
}
try {
  const tags = await request('tags');
  const installed = tags.models?.find((entry) => entry.name === model || entry.model === model);
  if (!installed) throw new Error(`Requested model is not installed: ${model}. This runner never downloads models or falls back externally.`);
  const details = await request('show', { model });
  if (details.remote_model || details.remote_host || !installed.size) throw new Error('Cloud-backed or unverified local model rejected');
  report.model_digest = installed.digest;
  report.ollama_version = (await request('version')).version;
  await save();
  for (const entry of cases) {
    console.log(`Evaluating synthetic case: ${entry.id}`);
    const started = performance.now();
    const result = { id: entry.id, contract_valid: false, semantic_support: 'not_evaluated', human_review_status: 'pending' };
    try {
      const response = await request('chat', {
        model, messages: buildNoteRequest(entry.input, prompt), format: providerNoteSchema,
        stream: false, think: false, keep_alive: '3m', options: report.settings,
      }, 240000);
      result.raw_content = response.message?.content ?? '';
      result.done_reason = response.done_reason ?? null;
      result.ollama_metrics = Object.fromEntries(['total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration'].map((key) => [key, response[key] ?? null]));
      if (response.done !== true || response.done_reason !== 'stop') throw new Error('Incomplete or truncated generation');
      result.output = JSON.parse(result.raw_content);
      result.validation = validateNotes(result.output, entry.input);
      result.contract_valid = true;
    } catch (error) { result.error = error.message; }
    result.wall_ms = Math.round(performance.now() - started);
    try { result.loaded_models = (await request('ps')).models?.map(({ name, size, size_vram, context_length }) => ({ name, size, size_vram, context_length })); }
    catch { result.loaded_models = null; }
    report.cases.push(result);
    await save();
    console.log(`${entry.id}: contract ${result.contract_valid ? 'valid' : 'failed'}; ${result.wall_ms} ms; semantic review pending`);
  }
  report.completed_at = new Date().toISOString();
  report.contract_valid_cases = report.cases.filter((entry) => entry.contract_valid).length;
  report.all_cases_contract_valid = report.contract_valid_cases === cases.length;
  await save();
  if (!report.all_cases_contract_valid) process.exitCode = 1;
} catch (error) {
  report.run_error = error.message;
  await save();
  console.error(error.message);
  process.exitCode = 2;
} finally {
  console.log(`Report: ${path.relative(root, directory)}/report.json`);
}
