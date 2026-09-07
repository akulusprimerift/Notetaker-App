export const MAX_PENDING_BYTES = 1024 ** 3;
export const MAX_IN_FLIGHT = 8 * 1024 ** 2;
export function encodeWav(samples, sampleRate) {
  if (!(samples instanceof Float32Array) || !samples.length || !Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 192000) throw new Error('Invalid PCM input');
  const buffer = new ArrayBuffer(44 + samples.length * 2), view = new DataView(buffer);
  const text = (offset, value) => { for (let i=0;i<value.length;i++) view.setUint8(offset+i,value.charCodeAt(i)); };
  text(0,'RIFF'); view.setUint32(4,buffer.byteLength-8,true); text(8,'WAVE'); text(12,'fmt ');
  view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
  view.setUint32(24,sampleRate,true); view.setUint32(28,sampleRate*2,true);
  view.setUint16(32,2,true); view.setUint16(34,16,true); text(36,'data'); view.setUint32(40,samples.length*2,true);
  for(let i=0;i<samples.length;i++) {
    const sample = Number.isFinite(samples[i]) ? Math.max(-1,Math.min(1,samples[i])) : 0;
    view.setInt16(44+i*2,Math.round(sample*(sample<0?32768:32767)),true);
  }
  return buffer;
}
export function matchesAck(identity, ack) {
  return ack?.storage_state === 'verified' && typeof ack.chunk_id === 'string' &&
    Object.keys(identity).every(key => identity[key] === ack[key]);
}
export function admissionBytes(sampleRate, minutes=60) { return Math.ceil(sampleRate*2*60*minutes*1.25); }
