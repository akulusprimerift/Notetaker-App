import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {encodeWav,matchesAck,admissionBytes} from '../../apps/web/public/capture/pcm.mjs';
import {Recorder} from '../../apps/web/public/capture/recorder.mjs';

test('stop waits for an older upload read before closing and sealing the journal',async()=>{
  const recorder=new Recorder({owner:'owner',lecture:'lecture',csrf:'csrf',onChange:()=>{}});
  let row={id:'run',admitted:true,stopped:false,server_sealed:false,gaps:[],samples:48000,next_sequence:1,pending_bytes:0};
  let releaseRead,readStarted,sealed=false,first=true;
  const reading=new Promise(resolve=>{readStarted=resolve;});
  recorder.run={...row};recorder.active=true;
  recorder.node={port:{postMessage:()=>queueMicrotask(()=>recorder.workerMessage({kind:'finished'}))},disconnect:()=>{}};
  recorder.journal={get:async()=>{
    const snapshot={...row};
    if(first){first=false;readStarted();await new Promise(resolve=>{releaseRead=resolve;});}
    return snapshot;
  },patch:async(_owner,_id,patch)=>(row={...row,...patch}),pending:async()=>[],list:async()=>[{...row}]};
  recorder.api=async(path)=>{if(path.endsWith('/seal'))sealed=true;return {manifest_version:1};};
  recorder.refresh=async()=>{};
  const uploading=recorder.sync();await reading;
  const stopping=recorder.stop();
  await new Promise(resolve=>setImmediate(resolve));releaseRead();
  await Promise.all([uploading,stopping]);
  assert.equal(row.stopped,true);assert.equal(sealed,true);assert.equal(row.server_sealed,true);
  assert.equal(recorder.working,false);assert.equal(recorder.run.stopped,true);
});

test('sleep flushes available audio, retains its gap after saves and never resumes capture',async()=>{
  const recorder=new Recorder({owner:'owner',lecture:'lecture',csrf:'csrf',onChange:()=>{}});
  let stopped=0,terminated=0,sealed;
  let row={id:'run',admitted:true,gaps:[],samples:48000,next_sequence:1,pending_bytes:0};
  recorder.run=row;recorder.active=true;
  recorder.stream={getTracks:()=>[{stop:()=>stopped++}]};
  recorder.node={port:{postMessage:()=>queueMicrotask(()=>recorder.workerMessage({kind:'finished'}))},disconnect:()=>{}};
  recorder.worker={terminate:()=>terminated++};
  recorder.journal={get:async()=>row,patch:async(_owner,_id,patch)=>(row={...row,...patch}),pending:async()=>[],list:async()=>[row]};
  recorder.api=async(path,body)=>{if(path.endsWith('/seal'))sealed=body;return {manifest_version:1};};
  recorder.refresh=async()=>{};
  await Promise.all([recorder.interrupt('suspend'),recorder.interrupt('resume')]);
  assert.equal(stopped,1);assert.equal(terminated,1);assert.equal(recorder.active,false);
  assert.deepEqual(sealed.gaps,[{reason:'sleep_or_suspension',after_sample:48000,unknown_extent:true}]);
  assert.equal(sealed.final_sample_count,48000);assert.equal(row.server_sealed,true);
  assert.match(recorder.message,/missing time was not recorded/);
  await recorder.interrupt('resume');assert.equal(stopped,1);
});

test('sleep cancels an in-flight microphone request before admission',async()=>{
  let resolveStream,stopped=0;
  const recorder=new Recorder({owner:'owner',lecture:'lecture',csrf:'csrf',onChange:()=>{},streamFactory:()=>new Promise(resolve=>{resolveStream=resolve;})});
  recorder.takeLock=async()=>{};recorder.refresh=async()=>{};
  recorder.server.available=true;recorder.journal={list:async()=>[]};
  const starting=recorder.start();
  while(!resolveStream)await new Promise(resolve=>setImmediate(resolve));
  await recorder.interrupt('suspend');
  resolveStream({getTracks:()=>[{stop:()=>stopped++}]});
  await starting;
  assert.equal(stopped,1);assert.equal(recorder.active,false);assert.equal(recorder.run,null);
  assert.match(recorder.message,/cancelled/);
});

test('PCM WAV preserves the actual sample rate, length and signed sample range',()=>{
  for(const rate of [44100,48000,96000]){
    const wav=encodeWav(new Float32Array([-2,-0.5,0,0.5,2,NaN]),rate),view=new DataView(wav);
    assert.equal(view.getUint32(24,true),rate);
    assert.equal(view.getUint32(28,true),rate*2);
    assert.equal(view.getUint32(40,true),12);
    assert.equal(wav.byteLength,56);
    assert.deepEqual(Array.from({length:6},(_,i)=>view.getInt16(44+2*i,true)),[-32768,-16384,0,16384,32767,0]);
  }
});
test('WAV encoder rejects empty audio and unsupported sample rates',()=>{
  assert.throws(()=>encodeWav(new Float32Array(),48000));
  assert.throws(()=>encodeWav(new Float32Array([1]),1));
});
test('every immutable identity field must match before releasing local audio',()=>{
  const identity={run_id:'run',capture_epoch:1,sequence:0,start_sample:0,sample_count:96000,sample_rate:48000,
    channels:1,encoding:'pcm_s16le_wav',sha256:'a'.repeat(64),byte_length:192044};
  const ack={...identity,chunk_id:'chunk',storage_state:'verified',manifest_version:1};
  assert(matchesAck(identity,ack));
  for(const key of Object.keys(identity))assert(!matchesAck(identity,{...ack,[key]:'wrong'}),key);
  assert(!matchesAck(identity,{...ack,storage_state:'reserved'}));
  assert(!matchesAck(identity,{...ack,chunk_id:null}));
});
test('one-hour headroom includes the declared 25 percent overhead',()=>{
  assert.equal(admissionBytes(48000),432000000);
});
const source=await readFile(new URL('../../apps/web/public/capture/worklet.js',import.meta.url),'utf8');
function worklet(){
  let Processor;
  class Base{constructor(){this.messages=[];this.port={postMessage:message=>this.messages.push(message)};}}
  vm.runInNewContext(source,{AudioWorkletProcessor:Base,sampleRate:8000,Float32Array,
    registerProcessor:(_name,type)=>{Processor=type;}});
  return new Processor();
}
test('worklet packages arbitrary block sizes with no lost samples and flushes its tail',()=>{
  const processor=worklet();
  const count=16000*2+177;
  let position=0;
  while(position<count){
    const block=new Float32Array(Math.min(173,count-position));block.fill(0.25);
    assert(processor.process([[block]]));position+=block.length;
  }
  processor.port.onmessage({data:{kind:'stop'}});
  assert.deepEqual(processor.messages.filter(m=>m.kind==='samples').map(m=>m.samples.length),[16000,16000,177]);
  assert(processor.messages.filter(m=>m.kind==='samples').every(m=>m.samples.every(sample=>sample===0.25)));
  assert.equal(processor.messages.at(-1).kind,'stopped');
  assert.equal(processor.process([[new Float32Array(128)]]),false);
});
test('worklet stops at bounded backlog without silently evicting queued audio',()=>{
  const processor=worklet();let count=0;
  while(processor.process([[new Float32Array(128)]])){count+=128;assert(count<3000000);}
  const retained=processor.messages.filter(m=>m.kind==='samples').reduce((sum,m)=>sum+m.samples.length,0);
  assert.equal(retained,count);
  assert(retained*4<=8*1024*1024);
  assert(processor.messages.some(m=>m.kind==='overflow'));
});
test('only persisted-buffer responses release worklet backpressure',()=>{
  const processor=worklet();
  processor.process([[new Float32Array(16000)]]);
  assert.equal(processor.pending,64000);
  processor.port.onmessage({data:{kind:'persisted',bytes:64000}});
  assert.equal(processor.pending,0);
});
test('default recorder transport binds fetch to the browser global receiver',async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=function(url){assert.equal(this,globalThis);assert.equal(url,'/api/lectures/lecture/capture');return Promise.resolve(new Response('{"available":true}',{headers:{'content-type':'application/json'}}));};
    const recorder=new Recorder({owner:'owner',lecture:'lecture',csrf:'test',onChange:()=>{}});
    assert.deepEqual(await recorder.api('/capture'),{available:true});
  }finally{globalThis.fetch=original;}
});
