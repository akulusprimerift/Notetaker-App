import {matchesAck,MAX_PENDING_BYTES} from './pcm.mjs';

export function openJournal(name='notetaker-capture-v1') {
  return new Promise((resolve,reject) => {
    const request=indexedDB.open(name,1);
    request.onupgradeneeded=()=>{
      request.result.createObjectStore('runs',{keyPath:['owner_id','id']});
      request.result.createObjectStore('chunks',{keyPath:['owner_id','run_id','sequence']});
    };
    request.onerror=()=>reject(request.error);
    request.onblocked=()=>reject(new Error('Close the other workspace tabs so local storage can open.'));
    request.onsuccess=()=>{
      const db=request.result;
      db.onversionchange=()=>db.close();
      resolve(new Journal(db));
    };
  });
}

class Journal {
  constructor(db) { this.db=db; }
  close() { this.db.close(); }
  transaction(stores,mode,work) {
    return new Promise((resolve,reject)=>{
      let tx;
      try { tx=this.db.transaction(stores,mode,{durability:'strict'}); }
      catch(error) { reject(error); return; }
      let result, failure;
      const set=value=>{result=value;}, fail=error=>{failure=error;tx.abort();};
      tx.oncomplete=()=>resolve(result); // A request success alone is not persistence.
      tx.onerror=()=>reject(failure??tx.error??new Error('Local storage failed.'));
      tx.onabort=()=>reject(failure??tx.error??new Error('Local storage could not preserve this audio.'));
      try { work(tx,set,fail); } catch(error) { fail(error); }
    });
  }
  list(owner,lecture) {
    return this.transaction(['runs'],'readonly',(tx,set)=>{
      tx.objectStore('runs').getAll().onsuccess=event=>set(event.target.result.filter(run=>run.owner_id===owner&&run.lecture_id===lecture));
    });
  }
  get(owner,id) { return this.transaction(['runs'],'readonly',(tx,set)=>{tx.objectStore('runs').get([owner,id]).onsuccess=event=>set(event.target.result);}); }
  put(run) { return this.transaction(['runs'],'readwrite',tx=>{tx.objectStore('runs').put(run);}); }
  patch(owner,id,changes) {
    return this.transaction(['runs'],'readwrite',(tx,set,fail)=>{
      const runs=tx.objectStore('runs');
      runs.get([owner,id]).onsuccess=event=>{
        const run=event.target.result;
        if(!run) {fail(new Error('The recovery journal is unavailable.'));return;}
        Object.assign(run,changes);runs.put(run);set(run);
      };
    });
  }
  append(owner,id,wav,sha256,count) {
    return this.transaction(['runs','chunks'],'readwrite',(tx,set,fail)=>{
      const runs=tx.objectStore('runs');
      runs.getAll().onsuccess=event=>{
        const all=event.target.result, run=all.find(row=>row.owner_id===owner&&row.id===id);
        if(!run || run.stopped) {fail(new Error('The recording journal is closed.'));return;}
        if(all.reduce((sum,row)=>sum+row.pending_bytes,0)+wav.byteLength>MAX_PENDING_BYTES) {fail(new Error('The local audio buffer is full. Recording stopped to preserve the audio already captured.'));return;}
        const identity={run_id:id,capture_epoch:run.capture_epoch,sequence:run.next_sequence,start_sample:run.samples,
          sample_count:count,sample_rate:run.sample_rate,channels:1,encoding:'pcm_s16le_wav',sha256,byte_length:wav.byteLength};
        tx.objectStore('chunks').add({owner_id:owner,run_id:id,sequence:run.next_sequence,identity,blob:new Blob([wav],{type:'audio/wav'})});
        run.next_sequence++;run.samples+=count;run.pending_bytes+=wav.byteLength;
        runs.put(run);set(run);
      };
    });
  }
  pending(owner,id) {
    return this.transaction(['chunks'],'readonly',(tx,set)=>{
      tx.objectStore('chunks').openCursor(IDBKeyRange.bound([owner,id,0],[owner,id,Number.MAX_SAFE_INTEGER])).onsuccess=event=>{
        const cursor=event.target.result;
        if(!cursor) {set([]);return;}
        if(cursor.value.blob) set([cursor.value]);
        else cursor.continue();
      };
    });
  }
  acknowledge(owner,id,sequence,ack) {
    return this.transaction(['runs','chunks'],'readwrite',(tx,set,fail)=>{
      const chunks=tx.objectStore('chunks'),runs=tx.objectStore('runs');
      chunks.get([owner,id,sequence]).onsuccess=event=>{
        const chunk=event.target.result;
        if(!chunk || !chunk.blob) {set(false);return;}
        if(!matchesAck(chunk.identity,ack)) {fail(new Error('The server acknowledgement does not match this audio. Its local copy was retained.'));return;}
        runs.get([owner,id]).onsuccess=found=>{
          const run=found.target.result;
          run.pending_bytes-=chunk.identity.byte_length;
          // Retain immutable metadata and the matching receipt, releasing only the blob.
          chunk.ack=ack;delete chunk.blob;
          runs.put(run);chunks.put(chunk);set(true);
        };
      };
    });
  }
  purge(owner,id) {
    return this.transaction(['runs','chunks'],'readwrite',tx=>{
      tx.objectStore('runs').delete([owner,id]);
      tx.objectStore('chunks').delete(IDBKeyRange.bound([owner,id,0],[owner,id,Number.MAX_SAFE_INTEGER]));
    });
  }
}
