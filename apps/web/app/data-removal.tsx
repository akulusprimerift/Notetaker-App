'use client';
import {useEffect,useRef,useState} from 'react';
import {purgeDrafts} from './note-drafts';
// @ts-expect-error Browser-native capture module.
import {openJournal} from '../public/capture/journal.mjs';
type Removal={id:string;lecture_id:string;kind:'audio'|'lecture';status:string;objects_total:number;objects_removed:number;error:string|null};
export default function DataRemoval({owner,csrf,onRemoved}:{owner:string;csrf:string;onRemoved:(lecture:string,kind:string)=>void}){
  const [rows,setRows]=useState<Removal[]>([]),[error,setError]=useState(''),[purged,setPurged]=useState<string[]>([]);
  const callback=useRef(onRemoved);useEffect(()=>{callback.current=onRemoved},[onRemoved]);
  useEffect(()=>{
    let stopped=false,running=false;const done=new Set<string>();
    const refresh=async()=>{
      if(running)return;running=true;
      try{
        const response=await fetch('/api/deletions',{cache:'no-store'});if(!response.ok)throw new Error('Could not check deletion progress.');
        const data:Removal[]=await response.json();if(stopped)return;setRows(data);
        for(const row of data){
          if(done.has(row.id))continue;
          // Unmount readers/recorders before purging. The IDB tombstones also fence
          // a late draft save or recorder setup from another tab.
          window.dispatchEvent(new CustomEvent('lecture-removed',{detail:row}));
          callback.current(row.lecture_id,row.kind);
          const journal=await openJournal();try{await journal.purgeLecture(owner,row.lecture_id)}finally{journal.close()}
          if(row.kind==='lecture'){
            await purgeDrafts(row.lecture_id);
            sessionStorage.removeItem('notetaker:transcript-draft:'+owner+':'+row.lecture_id);
          }
          const ack=await fetch('/api/deletions/'+row.id+'/browser-purged',{method:'POST',headers:{'X-CSRF-Token':csrf}});
          if(!ack.ok)throw new Error('Local copies were removed, but their confirmation needs another attempt.');
          done.add(row.id);if(!stopped)setPurged([...done]);
        }
        if(!stopped)setError('');
      }catch(e){if(!stopped)setError(e instanceof Error?e.message:'Browser cleanup needs another attempt.')}finally{running=false}
    };
    void refresh();const timer=setInterval(()=>void refresh(),2500);
    window.addEventListener('online',refresh);window.addEventListener('deletion-started',refresh);
    return()=>{stopped=true;clearInterval(timer);window.removeEventListener('online',refresh);window.removeEventListener('deletion-started',refresh)};
  },[owner,csrf]);
  if(!rows.length&&!error)return null;
  return <section className="capture-panel" aria-label="Deletion progress"><h2>Data removal</h2>{error&&<p className="error" role="alert">{error}</p>}
    {rows.map(row=><div key={row.id}><p role="status"><strong>{row.kind==='audio'?'Audio removal':'Lecture deletion'} · {row.status==='complete'?'Server cleanup complete':row.status==='retrying'?'Waiting to retry':'Removing data'}</strong> · {row.objects_removed} of {row.objects_total} audio objects removed</p><p className="small muted">{purged.includes(row.id)?'Copies in this browser have been removed.':'Removing copies from this browser…'} {row.error}</p></div>)}
    <p className="small muted">Other browsers remove their copies when they reconnect to this workspace. Disconnected copies and exported files cannot be erased remotely. Storage is checked again for late uploads.</p>
  </section>;
}
