'use client';
import {useEffect,useRef,useState} from 'react';
// @ts-expect-error Browser-native modules also run without a bundler in verification.
import {Recorder} from '../../public/capture/recorder.mjs';
// @ts-expect-error Browser-native module.
import {openJournal} from '../../public/capture/journal.mjs';
// @ts-expect-error Browser-native module.
import {encodeWav,MAX_PENDING_BYTES} from '../../public/capture/pcm.mjs';

// Development-only synthetic harness. It never requests microphone permission.
export default function CaptureCheck(){
  const [log,setLog]=useState<string[]>([]),[view,setView]=useState('No synthetic recording prepared.');
  const [runIds,setRunIds]=useState<string[]>([]),[lecture,setLecture]=useState('');
  const recorder=useRef<InstanceType<typeof Recorder>|null>(null),network=useRef(false),lostAck=useRef(false);
  const denyOnce=useRef(false);
  const say=(text:string)=>setLog(previous=>[...previous,text]);
  useEffect(()=>()=>{void recorder.current?.dispose();},[]);
  async function journalChecks(){
    const name='notetaker-test-'+crypto.randomUUID(),owner='synthetic-owner',id=crypto.randomUUID();
    let journal=await openJournal(name);
    const check=(condition:boolean,label:string)=>{if(!condition)throw new Error(label);say('PASS: '+label);};
    try{
      const run={id,owner_id:owner,lecture_id:'synthetic-lecture',capture_epoch:1,sample_rate:48000,next_sequence:0,samples:0,pending_bytes:0,stopped:false};
      await journal.put(run);
      const wav=encodeWav(new Float32Array([0,0.5,-0.5]),48000),hash='a'.repeat(64);
      await journal.append(owner,id,wav,hash,3);
      journal.close();journal=await openJournal(name);
      check((await journal.get(owner,id)).samples===3,'Blob and sample manifest survive closing and reopening IndexedDB');
      let chunk=(await journal.pending(owner,id))[0];
      let mismatch=false;
      try{await journal.acknowledge(owner,id,0,{...chunk.identity,storage_state:'verified',chunk_id:'server-chunk',sha256:'b'.repeat(64)});}catch{mismatch=true;}
      check(mismatch&&(await journal.pending(owner,id)).length===1,'Mismatched acknowledgement retains the original blob');
      await journal.acknowledge(owner,id,0,{...chunk.identity,storage_state:'verified',chunk_id:'server-chunk'});
      check((await journal.pending(owner,id)).length===0&&(await journal.get(owner,id)).pending_bytes===0,'Matching acknowledgement releases only the confirmed blob');
      await journal.patch(owner,id,{pending_bytes:MAX_PENDING_BYTES});
      let capacity=false;
      try{await journal.append(owner,id,wav,hash,3);}catch{capacity=true;}
      check(capacity&&(await journal.get(owner,id)).samples===3,'Capacity failure is atomic and preserves the prior manifest');
      let aborted=false;
      try{await journal.transaction(['runs'],'readwrite',(tx:IDBTransaction,_set:unknown,fail:(error:Error)=>void)=>{tx.objectStore('runs').delete([owner,id]);fail(new Error('synthetic abort'));});}catch{aborted=true;}
      check(aborted&&!!(await journal.get(owner,id)),'Aborted transaction does not remove the recovery journal');
      check((await journal.list('another-owner','synthetic-lecture')).length===0,'Local journal listing is owner scoped');
      await journal.purge(owner,id);
    }catch(error){say('FAIL: '+(error as Error).message);}finally{journal.close();indexedDB.deleteDatabase(name);}
  }
  async function prepare(){
    try{
      await recorder.current?.dispose();
      const sessionResponse=await fetch('/api/session'),session=await sessionResponse.json();
      if(!sessionResponse.ok)throw new Error('Unlock the main workspace first.');
      const headers={'Content-Type':'application/json','X-CSRF-Token':session.csrf_token,'Idempotency-Key':'m02-synthetic-course-v1'};
      const courseResponse=await fetch('/api/courses',{method:'POST',headers,body:JSON.stringify({name:'Capture checks (synthetic)',code:'DEV'})});
      if(!courseResponse.ok)throw new Error('Synthetic course could not be prepared.');
      const course=await courseResponse.json();
      let lectureId=location.hash.slice(1);
      if(!lectureId){
        const response=await fetch(`/api/courses/${course.id}/lectures`,{method:'POST',headers:{...headers,'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({title:'Generated tone — no microphone'})});
        if(!response.ok)throw new Error('Synthetic lecture could not be prepared.');
        lectureId=(await response.json()).id;location.hash=lectureId;
      }
      setLecture(lectureId);
      const instance=new Recorder({owner:session.owner_id,lecture:lectureId,csrf:session.csrf_token,
        onChange:(state:{active:boolean;working:boolean;message:string;local:{id:string;pending_bytes:number;samples:number}[];server:{runs:{id:string;complete:boolean;saved_through_samples:number;sealed:boolean;gaps:unknown[]}[]}})=>{
          setView(JSON.stringify({active:state.active,working:state.working,message:state.message,
            local:state.local.map(run=>({id:run.id,pending_bytes:run.pending_bytes,samples:run.samples})),
            runs:state.server.runs.map(run=>({id:run.id,complete:run.complete,sealed:run.sealed,saved_through_samples:run.saved_through_samples,gaps:run.gaps}))},null,2));
          setRunIds([...new Set([...state.server.runs.map(run=>run.id),...state.local.map(run=>run.id)])]);
        },streamFactory:async()=>{
          if(denyOnce.current){denyOnce.current=false;throw new DOMException('Synthetic permission denial','NotAllowedError');}
          const context=new AudioContext(),tone=context.createOscillator(),gain=context.createGain(),output=context.createMediaStreamDestination();
          tone.frequency.value=440;gain.gain.value=0.03;tone.connect(gain);gain.connect(output);tone.start();await context.resume();
          for(const track of output.stream.getTracks()){const original=track.stop.bind(track);track.stop=()=>{original();tone.stop();void context.close();};}
          return output.stream;
        },fetcher:async(input:RequestInfo,init:RequestInit)=>{
          if(network.current)throw new Error('Synthetic network interruption');
          const response=await fetch(input,init);
          if(lostAck.current&&init?.method==='PUT'&&response.ok){lostAck.current=false;say('Injected: one response lost after server upload completed');throw new Error('Synthetic lost acknowledgement');}
          return response;
        }});
      recorder.current=instance;await instance.init();say('Synthetic capture ready. No microphone is used.');
    }catch(error){say('FAIL: '+(error as Error).message);}
  }
  async function crash(){
    const instance=recorder.current;if(!instance)return;
    // Deliberate fault injection: leave the journal unsealed, as an abruptly lost page would.
    instance.closeMicrophone();instance.active=false;instance.disposed=true;clearInterval(instance.timer);
    instance.node?.disconnect();instance.source?.disconnect();instance.node=null;instance.source=null;
    if(instance.context){instance.context.onstatechange=null;await instance.context.close();instance.context=null;}
    instance.worker?.terminate();instance.worker=null;
    await instance.writeChain;await instance.syncPromise;
    instance.releaseLock?.();instance.releaseLock=null;
    window.removeEventListener('beforeunload',instance.beforeUnload);document.removeEventListener('click',instance.navigate,true);
    instance.journal.close();recorder.current=null;
    setView('Simulated abrupt recorder exit. The durable journal was left unsealed; reload and recover it.');
  }
  return <main style={{maxWidth:1000,margin:'30px auto',padding:24}}><h1>Capture verification — development only</h1><p>Generated tone and isolated browser-storage checks. No microphone is accessed. Network switches affect only this test recorder.</p>
    <div className="capture-controls"><button onClick={()=>void journalChecks()}>Run browser storage checks</button><button onClick={()=>void prepare()}>Prepare synthetic recording</button><button onClick={()=>void recorder.current?.start()}>Start synthetic recording</button><button onClick={()=>void recorder.current?.stop()}>Stop synthetic recording</button><button onClick={()=>{network.current=!network.current;say(network.current?'Network simulation: offline':'Network simulation: online');}}>Toggle simulated connection</button><button onClick={()=>{lostAck.current=true;say('Next upload response will be lost');}}>Lose next acknowledgement</button><button onClick={()=>{denyOnce.current=true;say('Next synthetic start will simulate permission denial');}}>Simulate permission denial</button><button onClick={()=>void recorder.current?.stop('sleep_or_suspension')}>Simulate suspension stop</button><button onClick={()=>void crash()}>Simulate abrupt recorder exit</button></div>
    {runIds.map((id,index)=><button key={id} onClick={()=>void recorder.current?.recover(id)}>Recover synthetic segment {index+1}</button>)}
    {lecture&&<p><a href={`/#lecture/${lecture}`}>Open this synthetic lecture</a></p>}
    <pre aria-label="Capture state" style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',fontSize:13}}>{view}</pre><pre aria-label="Verification results" style={{whiteSpace:'pre-wrap'}}>{log.join('\n')}</pre></main>;
}
