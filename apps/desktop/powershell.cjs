'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');

function powerShellCandidates({env = process.env, platform = process.platform} = {}) {
  if (platform !== 'win32') return ['pwsh'];
  const pathEntries = (env.Path || env.PATH || '').split(path.delimiter).filter(Boolean)
    .map(entry => entry.replace(/^"|"$/g, '').trim()).filter(Boolean)
    .map(entry => path.join(entry, 'pwsh.exe'));
  const known = [
    env.ProgramW6432 && path.join(env.ProgramW6432, 'PowerShell', '7', 'pwsh.exe'),
    env.ProgramFiles && path.join(env.ProgramFiles, 'PowerShell', '7', 'pwsh.exe'),
    env['ProgramFiles(x86)'] && path.join(env['ProgramFiles(x86)'], 'PowerShell', '7', 'pwsh.exe'),
    env.LOCALAPPDATA && path.join(env.LOCALAPPDATA, 'Microsoft', 'PowerShell', '7', 'pwsh.exe'),
  ].filter(Boolean);
  return [...new Set([...pathEntries, ...known])];
}

async function findPowerShell(options = {}) {
  const candidates = powerShellCandidates(options);
  for (const candidate of candidates) {
    try {
      await (options.access || fs.access)(candidate);
      return candidate;
    } catch {
      // Keep looking; a PATH entry can outlive an uninstalled PowerShell copy.
    }
  }
  return null;
}

module.exports = {findPowerShell, powerShellCandidates};
