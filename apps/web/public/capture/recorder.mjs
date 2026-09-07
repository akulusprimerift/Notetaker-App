import {openJournal} from './journal.mjs';
import {admissionBytes,MAX_PENDING_BYTES} from './pcm.mjs';

export class CaptureError extends Error {
  constructor(message,status=0,code='connection') {super(message);this.status=status;this.code=code;}
}

export class Recorder {
  constructor({owner,lecture,csrf,onChange,streamFactory,fetcher=globalThis.fetch.bind(globalThis)}) {
    Object.assign(this,{owner,lecture,csrf,onChange,streamFactory,fetcher});
    this.active=false;this.working=false;this.message='';this.local=[];this.server={available:false,runs:[],capture_epoch:0};
    this.writeChain=Promise.resolve();this.volatile=[];this.urls=[];this.disposed=false;
    this.beforeUnload=event=>{if(this.active||this.local.some(run=>run.pending_bytes)||this.volatile.length){event.preventDefault();event.returnValue='';}};
    this.navigate=event=>{
      if((this.active||this.working||this.volatile.length)&&event.target.closest?.('a[href]:not([download])')) {
        event.preventDefault();this.message='Stop recording and preserve any unsaved audio before leaving this lecture.';this.emit();
      }
    };
  }
  emit() {if(!this.disposed)this.onChange({active:this.active,working:this.working,message:this.message,local:this.local,server:this.server,emergency:this.urls});}
  async api(path='',body,extra={}) {
    let response;
    try {
      response=await this.fetcher(`/api/lectures/${this.lecture}${path}`,{cache:'no-store',signal:AbortSignal.timeout(20000),
        method:body===undefined?'GET':'POST',...extra,headers:{'Content-Type':'application/json','X-CSRF-Token':this.csrf,
          ...(this.run?{'X-Capture-Grant':this.run.grant}:{}),...extra.headers},body:body===undefined?undefined:JSON.stringify(body)});
    } catch {throw new CaptureError('The connection is unavailable. Unconfirmed audio stays in this browser for retry.');}
    const result=await response.json().catch(()=>null);
    if(!response.ok)throw new CaptureError(result?.error?.message??'Audio could not be saved. Its local copy was retained.',response.status,result?.error?.code);
    return result;
  }
  async init() {
    window.addEventListener('beforeunload',this.beforeUnload);
    document.addEventListener('click',this.navigate,true);
    try {
      this.journal=await openJournal();
      if(this.disposed){this.journal.close();return;}
    }catch(error){this.message='Local recovery storage could not open. Recording is unavailable. '+error.message;this.emit();return;}
    try {await this.refresh();}catch(error){this.message=error.message;this.emit();}
    if(this.disposed){this.journal.close();return;}
    this.timer=setInterval(()=>void this.tick(),3000);
  }
  async refresh() {
    this.server=await this.api('/capture');
    this.local=await this.journal.list(this.owner,this.lecture);
    this.emit();
  }
  async takeLock() {
    if(!navigator.locks)throw new Error('This browser cannot protect recording ownership. Use a current Chromium browser.');
    await new Promise((resolve,reject)=>{
      navigator.locks.request(`notetaker-capture:${this.owner}:${this.lecture}`,{ifAvailable:true},async lock=>{
        if(!lock){reject(new Error('This lecture is already recording or recovering in another tab.'));return;}
        await new Promise(release=>{this.releaseLock=release;resolve();});
      }).catch(reject);
    });
  }
  async start(takeover=false) {
    if(this.disposed||this.working||this.active)return;
    this.blocked=false;this.working=true;this.message='Checking microphone and recovery storage…';this.emit();
    try {
      await this.takeLock();await this.refresh();
      if(!this.server.available)throw new Error('Audio storage is unavailable. Recording has not started.');
      if(this.local.some(run=>!run.server_sealed||run.pending_bytes))throw new Error('Recover the previous recording on this browser before starting another segment.');
      const stream=this.streamFactory?await this.streamFactory():await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
      if(this.disposed){for(const track of stream.getTracks())track.stop();throw new Error('Recording setup was cancelled.');}
      this.stream=stream;this.context=new AudioContext();await this.context.resume();
      const rate=this.context.sampleRate;
      const estimate=await navigator.storage.estimate();
      const required=admissionBytes(rate);
      if(!estimate.quota||estimate.quota-(estimate.usage??0)<required||required>MAX_PENDING_BYTES)throw new Error('There is not enough browser storage for a one-hour recording buffer. Free some space before recording.');
      const persistent=await navigator.storage.persist().catch(()=>false);
      if(this.disposed)throw new Error('Recording setup was cancelled.');
      this.run={id:crypto.randomUUID(),owner_id:this.owner,lecture_id:this.lecture,grant:crypto.randomUUID()+crypto.randomUUID(),
        sample_rate:rate,capture_epoch:this.server.capture_epoch+1,expected_capture_epoch:this.server.capture_epoch,
        command:crypto.randomUUID(),takeover,admitted:false,persistent,stopped:false,server_sealed:false,
        next_sequence:0,samples:0,pending_bytes:0,gaps:[]};
      await this.journal.put(this.run); // Persist retry identity before making the admission request.
      const admitted=await this.admit(this.run);
      if(this.disposed)throw new Error('Recording setup was cancelled. Recover the prepared segment when reopening.');
      this.run=await this.journal.patch(this.owner,this.run.id,{admitted:true,capture_epoch:admitted.capture_epoch,gaps:admitted.gaps});
      await this.context.audioWorklet.addModule('/capture/worklet.js');
      if(this.disposed)throw new Error('Recording setup was cancelled.');
      this.worker=new Worker('/capture/worker.mjs',{type:'module'});
      this.node=new AudioWorkletNode(this.context,'lecture-capture',{channelCount:1,channelCountMode:'explicit',numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1]});
      this.source=this.context.createMediaStreamSource(stream);
      this.worker.onmessage=event=>this.workerMessage(event.data);
      this.worker.onerror=()=>{this.message='Audio packaging stopped. Recover saved chunks before continuing.';void this.stop('storage_failure');};
      this.node.onprocessorerror=()=>{this.message='The audio processor stopped. Recover this segment before continuing.';void this.stop('microphone_lost');};
      this.node.port.onmessage=({data})=>{
        if(data.kind==='samples')this.worker.postMessage({kind:'samples',samples:data.samples,sampleRate:rate},[data.samples.buffer]);
        if(data.kind==='overflow'){this.message='Local storage could not keep up. Recording has stopped.';void this.stop('storage_failure');}
        if(data.kind==='stopped')this.worker?.postMessage({kind:'finish'});
      };
      for(const track of stream.getAudioTracks()) {
        track.onended=()=>void this.stop('microphone_lost');
        track.onmute=()=>void this.stop('microphone_lost');
      }
      this.startedAt=Date.now();this.latestSampleAt=Date.now();this.active=true;
      this.context.onstatechange=()=>{if(this.active&&this.context.state!=='running')void this.stop('sleep_or_suspension');};
      this.source.connect(this.node);this.node.connect(this.context.destination);
      this.message=persistent?'Recording. Audio is being saved on this device.':'Recording. Browser persistence was not granted; keep this page open until every segment is confirmed saved.';
    } catch(error) {
      this.message=error.name==='NotAllowedError'?'Microphone access was declined. Allow it in your browser, then try again.':error.message;
      this.closeMicrophone();
      if(this.context){await this.context.close().catch(()=>{});this.context=null;}
      if(this.run)await this.journal.patch(this.owner,this.run.id,{stopped:true}).catch(()=>{});
      this.releaseLock?.();this.releaseLock=null;
    } finally {this.working=false;if(!this.disposed)this.local=await this.journal.list(this.owner,this.lecture);this.emit();}
  }
  admit(run) {
    return this.api(run.takeover?'/capture-takeover':'/capture-runs',{
      run_id:run.id,grant:run.grant,sample_rate:run.sample_rate,expected_capture_epoch:run.expected_capture_epoch
    },{headers:{'Idempotency-Key':run.command}});
  }
  workerMessage(data) {
    if(data.kind==='chunk') {
      this.latestSampleAt=Date.now();
      this.writeChain=this.writeChain.then(async()=>{
        try {
          this.run=await this.journal.append(this.owner,this.run.id,data.wav,data.sha256,data.count);
          this.node?.port.postMessage({kind:'persisted',bytes:data.sourceBytes});
          this.local=await this.journal.list(this.owner,this.lecture);this.emit();
        }catch(error){
          // A failed journal write is never reported as saved. Keep its bounded RAM copy available.
          this.volatile.push(data);
          const url=URL.createObjectURL(new Blob([data.wav],{type:'audio/wav'}));
          this.urls.push({url,name:`unsaved-audio-${this.urls.length+1}.wav`});
          this.message=error.message+' Download the unsaved audio below before closing this page.';
          void this.stop('storage_failure');
        }
      });
    }
    if(data.kind==='finished')this.flushResolve?.();
    if(data.kind==='failed'){this.message='Audio packaging failed. Recording stopped; recover the saved segment.';void this.stop('storage_failure');}
  }
  closeMicrophone() {
    for(const track of this.stream?.getTracks()??[]) {track.onended=null;track.onmute=null;track.stop();}
    this.stream=null;
  }
  async stop(reason) {
    if(this.stopPromise)return this.stopPromise;
    if(!this.active&&!this.node)return;
    this.stopPromise=this.finish(reason).finally(()=>{this.stopPromise=null;});
    return this.stopPromise;
  }
  async finish(reason) {
    this.active=false;this.working=true;this.closeMicrophone();this.emit();
    try {
      const flush=new Promise(resolve=>{this.flushResolve=resolve;});
      this.node?.port.postMessage({kind:'stop'});
      let timeout;
      const flushed=await Promise.race([flush.then(()=>true),new Promise(resolve=>{timeout=setTimeout(()=>resolve(false),5000);})]);
      clearTimeout(timeout);
      if(!flushed)reason=reason??'sleep_or_suspension';
      await this.writeChain;
      this.run=await this.journal.get(this.owner,this.run.id);
      const gaps=[...this.run.gaps];
      if(reason)gaps.push({reason,after_sample:this.run.samples,unknown_extent:true});
      this.run=await this.journal.patch(this.owner,this.run.id,{stopped:true,gaps});
      if(!this.volatile.length)this.message=reason?'Recording stopped after an interruption. Saved audio is retained; the missing interval will stay marked.':'Recording stopped. Confirming the remaining audio…';
      await this.sync();
    } catch(error) {this.message=error.message;}
    finally {
      this.node?.disconnect();this.source?.disconnect();this.node=null;this.source=null;
      if(this.context){this.context.onstatechange=null;await this.context.close().catch(()=>{});this.context=null;}
      this.worker?.terminate();this.worker=null;
      this.releaseLock?.();this.releaseLock=null;this.working=false;
      this.local=await this.journal.list(this.owner,this.lecture);this.emit();
    }
  }
  async tick() {
    if(this.disposed)return;
    if(this.active&&Date.now()-this.latestSampleAt>6500) {await this.stop('sleep_or_suspension');return;}
    if(!this.blocked&&(this.active || (this.run?.stopped&&(!this.run.server_sealed||this.run.pending_bytes))))await this.sync();
    else if(!this.working)await this.refresh().catch(()=>{});
  }
  async sync() {
    if(this.syncPromise)return this.syncPromise;
    this.syncPromise=this.uploadPending().catch(async error=>{
      this.message=error.message;
      if(error.status===401||error.status===404||['capture_fenced','capture_interrupted','capture_grant'].includes(error.code)) {
        this.blocked=true;
        if(this.active)void this.stop(error.status===401?'sleep_or_suspension':'takeover');
        if(error.status===404&&error.code==='unavailable'&&this.run)await this.journal.purge(this.owner,this.run.id);
      }
      this.emit();
    }).finally(()=>{this.syncPromise=null;});
    return this.syncPromise;
  }
  async uploadPending() {
    if(!this.run?.admitted)return;
    await this.api(`/capture-runs/${this.run.id}/heartbeat`,{});
    while(true) {
      const pending=await this.journal.pending(this.owner,this.run.id);
      if(!pending.length)break;
      const chunk=pending[0];
      let response;
      try {response=await this.fetcher(`/api/lectures/${this.lecture}/capture-runs/${this.run.id}/chunks/${chunk.sequence}`,{
        method:'PUT',body:chunk.blob,signal:AbortSignal.timeout(20000),headers:{'Content-Type':'audio/wav','X-CSRF-Token':this.csrf,
          'X-Capture-Grant':this.run.grant,'X-Chunk-Identity':JSON.stringify(chunk.identity)}});}
      catch {throw new CaptureError('Connection interrupted. Recording can continue into the local buffer; unconfirmed audio is retained.');}
      const ack=await response.json().catch(()=>null);
      if(!response.ok)throw new CaptureError(ack?.error?.message??'Audio save failed. The local copy remains.',response.status,ack?.error?.code);
      await this.journal.acknowledge(this.owner,this.run.id,chunk.sequence,ack);
      this.run=await this.journal.get(this.owner,this.run.id);
      this.local=await this.journal.list(this.owner,this.lecture);this.emit();
      await this.api(`/capture-runs/${this.run.id}/heartbeat`,{});
    }
    this.run=await this.journal.get(this.owner,this.run.id);
    if(this.run.stopped&&!this.run.server_sealed) {
      const saved=await this.api(`/capture-runs/${this.run.id}/manifest`);
      await this.api(`/capture-runs/${this.run.id}/seal`,{expected_version:saved.manifest_version,last_sequence:this.run.next_sequence-1,final_sample_count:this.run.samples,gaps:this.run.gaps});
      this.run=await this.journal.patch(this.owner,this.run.id,{server_sealed:true});
    }
    await this.refresh();
    if(this.run.stopped&&this.run.server_sealed&&!this.volatile.length)this.message='This recording segment is saved. Follow transcription progress below.';
    else if(this.active)this.message='Recording. Audio is being saved on this device.';
    this.emit();
  }
  async recover(runId) {
    if(this.active||this.working)return;
    this.blocked=false;this.working=true;this.message='Recovering this recording segment…';this.emit();
    try {
      await this.takeLock();await this.refresh();
      let local=await this.journal.get(this.owner,runId);
      if(local&&!local.admitted) {
        this.run=local;
        const admitted=await this.admit(local);
        local=await this.journal.patch(this.owner,runId,{admitted:true,capture_epoch:admitted.capture_epoch,gaps:admitted.gaps});
        await this.refresh();
      }
      const server=this.server.runs.find(run=>run.id===runId);
      if(!server)throw new Error('This recording is unavailable. Its local copy was retained.');
      if(!local) {
        const last=Math.max(-1,...server.chunks.map(chunk=>chunk.sequence));
        const samples=Math.max(0,...server.chunks.map(chunk=>chunk.start_sample+chunk.sample_count));
        local={id:runId,owner_id:this.owner,lecture_id:this.lecture,admitted:true,capture_epoch:server.capture_epoch,
          sample_rate:server.sample_rate,stopped:false,server_sealed:false,pending_bytes:0,
          next_sequence:server.sealed?server.last_sequence+1:last+1,samples:server.sealed?server.final_sample_count:samples,gaps:server.gaps};
        await this.journal.put(local);
      }
      // Save recovery credentials before the request so a lost response remains retryable.
      if(!local.recovery_command||!local.recovery_body) {
        const body={run_id:runId,grant:crypto.randomUUID()+crypto.randomUUID(),
          expected_version:server.manifest_version,expected_capture_epoch:this.server.capture_epoch,
          last_sequence:local.next_sequence-1,final_sample_count:local.samples,gaps:local.gaps,interrupted:!local.stopped};
        local=await this.journal.patch(this.owner,runId,{recovery_command:crypto.randomUUID(),recovery_body:body});
      }
      this.run=local;
      const result=await this.api('/capture-recovery',local.recovery_body,
        {headers:{'Idempotency-Key':local.recovery_command}});
      this.run=await this.journal.patch(this.owner,runId,{grant:local.recovery_body.grant,stopped:true,server_sealed:true,gaps:result.gaps});
      await this.sync();
      await this.refresh();
      const updated=this.server.runs.find(run=>run.id===runId);
      this.message=updated?.complete?'Available audio recovered. Any interruption remains marked.':'Recovery saved what is available. Some declared audio is still missing; keep its original browser copy.';
    }catch(error){
      if(error.code==='recovery_version')await this.journal.patch(this.owner,runId,{recovery_command:null});
      this.message=error.message;
    }
    finally {this.releaseLock?.();this.releaseLock=null;this.working=false;this.emit();}
  }
  async dispose() {
    this.disposed=true;clearInterval(this.timer);
    this.closeMicrophone();
    await this.stop();await this.syncPromise;
    if(this.context){await this.context.close().catch(()=>{});this.context=null;}
    this.releaseLock?.();this.releaseLock=null;
    window.removeEventListener('beforeunload',this.beforeUnload);document.removeEventListener('click',this.navigate,true);
    this.journal?.close();
    for(const {url} of this.urls)URL.revokeObjectURL(url);
  }
  releaseEmergency() {
    if(this.active)return;
    for(const {url} of this.urls)URL.revokeObjectURL(url);
    this.urls=[];this.volatile=[];
    this.message='Emergency copies acknowledged. The interrupted segment remains marked as incomplete.';this.emit();
  }
  async cancelSetup(id) {
    if(this.active||this.working)return;
    this.working=true;this.emit();
    try {
      await this.takeLock();await this.refresh();
      const local=await this.journal.get(this.owner,id);
      if(this.server.runs.some(run=>run.id===id))throw new Error('This setup was accepted by the server. Recover its segment to close it.');
      if(!local||local.admitted||local.samples||local.pending_bytes)throw new Error('This journal may hold recorded audio. Use recovery to preserve it.');
      await this.journal.purge(this.owner,id);
      if(this.run?.id===id)this.run=null;
      this.message='Unused setup cleared. No audio was recorded.';await this.refresh();
    }catch(error){this.message=error.message;}
    finally {this.releaseLock?.();this.releaseLock=null;this.working=false;this.emit();}
  }
}
