'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
type Final={id:string;status:string;issues:string[];snapshot_id:string|null;created_at:string};
type State={cursor:number;edit_version:number;audio_removed:boolean;status:string;history:Final[]};
type Saved={title:string;issues:string[];notes:{content:{blocks:{id:string;topic:string;passages:{id:string;text:string}[]}[]}}|null;transcript:{segments:{id:string;text:string}[]}|null};
export default function Finalization({lecture,csrf,busy,onRemoved}:{lecture:string;csrf:string;busy:boolean;onRemoved:(lecture:string,kind:string)=>void}){
  const [state,setState]=useState<State|null>(null),[error,setError]=useState(''),[working,setWorking]=useState(false),[confirm,setConfirm]=useState<'final'|'available'|'reopen'|'audio'|'lecture'|null>(null),[view,setView]=useState<Saved|null>(null);
  const command=useRef<{body:string;path:string;key:string}|null>(null);
  const base='/api/lectures/'+lecture;
  const refresh=useCallback(async()=>{const response=await fetch(base+'/finalization',{cache:'no-store'});if(response.ok)setState(await response.json());else if(response.status!==404)throw new Error('Could not load finalization progress.')},[base]);
  useEffect(()=>{void refresh().catch(e=>setError(e.message));const timer=setInterval(()=>void refresh().catch(e=>setError(e.message)),2500);return()=>clearInterval(timer)},[refresh]);
  async function act(){
    if(!state||!confirm)return;setWorking(true);setError('');
    const removing=confirm==='audio'||confirm==='lecture';
    const path=base+(removing?'/deletion':confirm==='reopen'?'/finalization/reopen':'/finalization');
    const body=JSON.stringify(removing?{kind:confirm,expected_cursor:state.cursor}:{expected_cursor:state.cursor,expected_edit_version:state.edit_version,available_only:confirm==='available'});
    if(command.current?.body!==body||command.current.path!==path)command.current={body,path,key:crypto.randomUUID()};
    try{
      const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':command.current.key},body});const data=await response.json();if(!response.ok)throw new Error(data.error?.message??'This action needs another attempt.');
      command.current=null;
      if(removing){window.dispatchEvent(new CustomEvent('lecture-removed',{detail:{lecture_id:lecture,kind:confirm}}));onRemoved(lecture,confirm);window.dispatchEvent(new Event('deletion-started'));}
      if(confirm==='reopen')window.dispatchEvent(new CustomEvent('lecture-reopened',{detail:{lecture}}));
      setConfirm(null);await refresh();
    }catch(e){setError(e instanceof Error?e.message:'Could not finish the action.');await refresh().catch(()=>{})}finally{setWorking(false)}
  }
  const latest=state?.history[0];
  const labels:Record<string,string>={speech:'Finishing available speech…',notes:'Writing final notes…',needs_attention:'Finalization needs attention',complete:'Final snapshot saved',incomplete:'Final snapshot saved with incomplete results',cancelled:'Finalization superseded or cancelled'};
  return <section className="capture-panel" aria-label="Finalization and data control"><h2>Finalize and manage this lecture</h2>
    <p className="muted">Finalizing closes audio intake, finishes available transcription and notes, then saves a permanent snapshot. Your revision history remains available. Unsaved browser audio is excluded; recover it first if you need it.</p>
    {error&&<p role="alert" className="error">{error}</p>}
    {latest&&<><p role="status"><strong>{labels[latest.status]??latest.status}</strong></p>{latest.issues.map((issue,i)=><p className="gap-notice" key={i}>{issue}</p>)}</>}
    {busy&&<p className="small muted">Stop recording and finish any transcript correction before finalizing or removing data.</p>}
    <div className="capture-controls"><button className="primary" disabled={busy||working||!state} onClick={()=>setConfirm('final')}>{latest?.status==='needs_attention'?'Retry finalization':'Finalize lecture'}</button>
    {state&&!state.audio_removed&&['finalizing','finalized'].includes(state.status)&&<button className="secondary" disabled={busy||working} onClick={()=>setConfirm('reopen')}>Reopen for late audio</button>}
    <button className="secondary" disabled={busy||working||!state} onClick={()=>setConfirm('available')}>Finalize available results now</button>
    <button className="secondary" disabled={busy||working||!state||state.audio_removed} onClick={()=>setConfirm('audio')}>Remove audio</button>
    <button className="secondary" disabled={busy||working||!state} onClick={()=>setConfirm('lecture')}>Delete lecture</button></div>
    {confirm&&<div className="recovery-box" role="group" aria-label="Confirm data action"><h3>{confirm==='reopen'?'Reopen recording recovery?':confirm==='lecture'?'Delete this lecture permanently?':confirm==='audio'?'Remove all audio permanently?':confirm==='available'?'Save an incomplete final snapshot now?':'Finish this lecture?'}</h3>
      <p>{confirm==='reopen'?'Earlier final snapshots stay unchanged. Recover buffered audio or record another segment, then finalize again to create a new snapshot.':confirm==='lecture'?'This removes the lecture, transcript, notes, revision history, final snapshots and audio. Browser copies are removed on reconnect. Exported files are outside the app.':confirm==='audio'?'This removes audio and browser audio buffers. Transcript, notes, revisions and final snapshots stay saved. Playback and speech retry will no longer be available.':confirm==='available'?'Pending processing will be cancelled. Only saved transcript and notes are included, with incomplete results clearly marked. Unsaved note drafts are not part of the final snapshot.':'Audio intake closes immediately, including uploads from other tabs. Saved audio is processed and the selected saved notes are protected. Unsaved note drafts are not part of the final snapshot.'}</p>
      <button className="primary" disabled={busy||working} onClick={()=>void act()}>{working?'Working…':'Confirm'}</button> <button className="secondary" disabled={working} onClick={()=>setConfirm(null)}>Cancel</button>
    </div>}
    {!!state?.history.length&&<details><summary>Final snapshot history ({state.history.filter(row=>row.snapshot_id).length})</summary>{state.history.filter(row=>row.snapshot_id).map(row=><div key={row.id}><p>{new Date(row.created_at).toLocaleString()} · {labels[row.status]}</p><a className="text-button" href={base+'/final-snapshots/'+row.snapshot_id+'/export'}>Export final snapshot</a> <button className="text-button" onClick={async()=>{try{const response=await fetch(base+'/final-snapshots/'+row.snapshot_id);if(!response.ok)throw new Error('Snapshot unavailable.');setView(await response.json())}catch(e){setError((e as Error).message)}}}>Read snapshot</button></div>)}</details>}
    {view&&<section className="recovery-box" aria-label="Saved final snapshot"><button className="text-button" onClick={()=>setView(null)}>Close snapshot</button><h3>{view.title}</h3>{view.issues.map((text,i)=><p key={i} className="gap-notice">{text}</p>)}{view.notes?.content.blocks.map(block=><div key={block.id}><h4>{block.topic}</h4>{block.passages.map(p=><p className="study-text" key={p.id}>{p.text}</p>)}</div>)}<details><summary>Snapshot transcript</summary>{view.transcript?.segments.map(p=><p className="study-text" key={p.id}>{p.text}</p>)}</details></section>}
  </section>;
}
