'use strict';
const element = id => document.getElementById(id);
async function run(action) {
  element('error').textContent = '';
  try { await action(); } catch (error) { element('error').textContent = error.message; }
}
async function status() {
  const value = await window.desktopSetup.status();
  element('status').textContent = value.message;
  element('location').textContent = 'Windows app data: ' + value.dataPath;
  element('start').disabled = value.starting;
}
async function models() {
  const value = await window.desktopSetup.models();
  element('models').textContent = [value.ollamaAvailable ? 'Ollama is available.' : 'Ollama is not running or cannot be reached.',
    ...value.ollama.map(m => 'Ollama: ' + m.name),
    ...(!value.ollamaAvailable ? value.ollamaManifests.map(name => 'Installed Ollama manifest: ' + name + ' (start Ollama to verify availability)') : []),
    value.speech ? 'Speech: ' + value.speech.path : 'No configured local speech model found. Choose an existing faster-whisper model folder.',
    ...value.otherFiles.map(m => 'Detected: ' + m.path + '\n' + m.status)].join('\n');
}
element('start').onclick = () => run(async () => {element('start').disabled=true;await window.desktopSetup.start();await status();});
element('open').onclick = () => run(() => window.desktopSetup.open());
element('refresh').onclick = () => run(models);
element('speech').onclick = () => run(async () => {await window.desktopSetup.speechFolder();await models();});
void run(async () => {await status();await models();});
setInterval(() => {void run(status);}, 3000);
