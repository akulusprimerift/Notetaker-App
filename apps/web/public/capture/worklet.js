class LectureCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(Math.round(sampleRate*2));
    this.used = 0; this.pending = 0; this.stopped = false;
    this.port.onmessage = ({data}) => {
      if(data.kind === 'persisted') this.pending = Math.max(0,this.pending-data.bytes);
      if(data.kind === 'stop' && !this.stopped) { this.stopped=true; this.flush(); this.port.postMessage({kind:'stopped'}); }
    };
  }
  flush() {
    if(!this.used) return;
    const samples = this.buffer.slice(0,this.used);
    this.pending += samples.byteLength;
    this.port.postMessage({kind:'samples', samples},[samples.buffer]);
    this.used = 0;
  }
  process(inputs) {
    if(this.stopped) return false;
    const input = inputs[0]?.[0];
    if(!input) return true;
    // Stop at the bound; never discard a queued, unacknowledged chunk to keep recording.
    if(this.pending + this.used*4 + input.byteLength > 8*1024*1024) {
      this.stopped=true; this.flush(); this.port.postMessage({kind:'overflow'}); this.port.postMessage({kind:'stopped'}); return false;
    }
    for(let offset=0;offset<input.length;) {
      const count = Math.min(this.buffer.length-this.used,input.length-offset);
      this.buffer.set(input.subarray(offset,offset+count),this.used);
      this.used += count; offset += count;
      if(this.used === this.buffer.length) this.flush();
    }
    return true; // Output stays silent; the microphone is not played through the speakers.
  }
}
registerProcessor('lecture-capture',LectureCapture);
