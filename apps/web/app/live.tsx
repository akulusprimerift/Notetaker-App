'use client';
import {useEffect,useState} from 'react';

// Full snapshots and their cursor are applied together. A reconnect never clears
// visible content, focus, source playback or an unsaved transcript correction.
export default function LiveUpdates({lecture,onSessionExpired}:{lecture:string;onSessionExpired:()=>void}){
  const [status,setStatus]=useState('Connecting live updates…');
  const [delay,setDelay]=useState<number|null>(null);
  useEffect(()=>{
    let stopped=false, socket:WebSocket|null=null, retry:ReturnType<typeof setTimeout>|undefined;
    let cursor:number|null=null, attempts=0, loading=false, again=false, resetRequested=false;
    const refresh=async(reset=false)=>{
      resetRequested ||= reset;
      if(loading){again=true;return;} loading=true;
      try{
        do {
          again=false;
          const applyReset=resetRequested;resetRequested=false;
          const response=await fetch(`/api/lectures/${lecture}/snapshot`,{cache:'no-store'});
          if(response.status===401){stopped=true;onSessionExpired();return;}
          if(!response.ok)throw new Error('snapshot unavailable');
          const snapshot=await response.json();
          if(stopped)return;
          if(applyReset||cursor===null||snapshot.update_cursor>=cursor){
            window.dispatchEvent(new CustomEvent('lecture-snapshot',{detail:{lecture,snapshot}}));
            cursor=snapshot.update_cursor;
            setDelay(snapshot.transcript.processing_delay_seconds);
          }
        } while(again&&!stopped);
      } finally {loading=false;}
    };
    const connect=async()=>{
      if(stopped)return;
      try{
        await refresh();if(stopped)return;
        const url=new URL(`/api/lectures/${lecture}/updates`,window.location.href);
        url.protocol=location.protocol==='https:'?'wss:':'ws:';
        if(cursor!==null)url.searchParams.set('after',String(cursor));
        socket=new WebSocket(url);
        socket.onopen=()=>{attempts=0;setStatus('Live updates connected');};
        socket.onmessage=event=>{
          try{
            const message=JSON.parse(event.data);
            if(message.schema_version!==1)return;
            // Duplicate/out-of-order invalidations are harmless. Heartbeats also
            // refresh job progress, which is independent of content revisions.
            if(message.kind==='snapshot_required'||message.kind==='heartbeat'||message.cursor> (cursor??-1)){
              void refresh(message.kind==='snapshot_required').catch(()=>{setStatus('Reconnecting live updates…');socket?.close();});
            }
          }catch{socket?.close();}
        };
        socket.onclose=event=>{
          if(stopped)return;
          if(event.code===1008){stopped=true;setStatus('Live access expired. Reopen the lecture.');return;}
          setStatus('Reconnecting · your reading position is retained');
          retry=setTimeout(()=>void connect(),Math.min(15000,1000*2**attempts++));
        };
        socket.onerror=()=>socket?.close();
      }catch{
        if(!stopped){setStatus('Waiting for connection · saved content stays visible');retry=setTimeout(()=>void connect(),4000);}
      }
    };
    void connect();
    return()=>{stopped=true;clearTimeout(retry);socket?.close();};
  },[lecture,onSessionExpired]);
  return <div className="live-progress" role="status"><strong>{status}</strong><span>{delay===null?'Checking processing delay…':`${delay.toFixed(1)} seconds of saved audio awaiting transcription`}</span><span className="small muted">Processing can fall behind while recording continues. Audio save progress is shown separately above.</span></div>;
}
