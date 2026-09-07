import {encodeWav} from './pcm.mjs';
let chain = Promise.resolve();
self.onmessage = ({data}) => {
  chain = chain.then(async () => {
    if(data.kind === 'finish') { self.postMessage({kind:'finished'}); return; }
    const wav = encodeWav(data.samples,data.sampleRate);
    const hash = await crypto.subtle.digest('SHA-256',wav);
    const sha256 = Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
    self.postMessage({kind:'chunk',wav,sha256,count:data.samples.length,sourceBytes:data.samples.byteLength},[wav]);
  }).catch(() => self.postMessage({kind:'failed'}));
};
