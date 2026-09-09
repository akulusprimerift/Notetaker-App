'use strict';
const ORIGIN = 'http://127.0.0.1:3000';
function localPage(value) {
  try { const url = new URL(value); return url.origin === ORIGIN && !url.username && !url.password; }
  catch { return false; }
}
function audioPermission(contents, permission, details = {}) {
  return permission === 'media' && localPage(contents?.getURL() || '') &&
    localPage(details.requestingUrl || details.securityOrigin || ORIGIN) &&
    Array.isArray(details.mediaTypes) && details.mediaTypes.length > 0 &&
    details.mediaTypes.every(type => type === 'audio');
}
module.exports = {ORIGIN, localPage, audioPermission};
