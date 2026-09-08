'use client';
import {useEffect,useRef,useState} from 'react';
import type {Revision} from './notes';
import {drafts,saveDraft,deleteDraft,type Draft} from './note-drafts';

export type Editing={version:number;selected:Revision|null;proposal:Revision|null;proposal_valid:boolean;sources_changed:boolean};
type History={edits:{id:string;version:number;action:string}[];generated:{id:string;version:number}[]};
type Props={lecture:string;revision:Revision;editing:Editing;csrf:string;onSaved:(revision:Revision)=>void;onExpired:()=>void};

export default function NoteEditor({lecture,revision,editing,csrf,onSaved,onExpired}:Props){
  const [draft,setDraft]=useState<Draft|null>(null),[recoverable,setRecoverable]=useState<Draft[]>([]);
  const [message,setMessage]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [compare,setCompare]=useState(false),[chosen,setChosen]=useState<string[]>([]),[history,setHistory]=useState<History|null>(null);
  const mounted=useRef(true),pending=useRef(Promise.resolve()),sequence=useRef(0);
  const command=useRef<{body:string;key:string}|null>(null);
  const path=`/api/lectures/${encodeURIComponent(lecture)}/notes`;
  useEffect(()=>{
    mounted.current=true;
    void drafts(lecture).then(rows=>{if(mounted.current)setRecoverable(rows)}).catch(()=>setError('Local drafts could not be opened. Keep this page open until your changes are saved.'));
    return()=>{mounted.current=false};
  },[lecture]);
  useEffect(()=>{setChosen([])},[editing.proposal?.id]);
  const persist=(value:Draft)=>{
    setDraft(value);setError('');setMessage('Saving draft on this device…');
    const ticket=++sequence.current;
    // Ordered writes prevent a slow older keystroke from replacing newer text.
    pending.current=pending.current.catch(()=>{}).then(()=>saveDraft(value)).then(()=>{
      if(mounted.current&&ticket===sequence.current)setMessage('Draft saved on this device. Export uses the saved revision.');
    }).catch(()=>{if(mounted.current)setError('Could not preserve this draft on this device. Keep this page open and save your changes to the lecture.');throw new Error('Draft storage unavailable')});
    void pending.current.catch(()=>{});
  };
  function start(){
    persist({id:crypto.randomUUID(),lecture,base_id:revision.id,expected_version:editing.version,
      passages:Object.fromEntries(revision.content.blocks.flatMap(b=>b.passages.map(p=>[p.id,p.text]))),
      topics:Object.fromEntries(revision.content.blocks.map(b=>[b.id,b.topic])),
      base_passages:Object.fromEntries(revision.content.blocks.flatMap(b=>b.passages.map(p=>[p.id,p.text]))),
      base_topics:Object.fromEntries(revision.content.blocks.map(b=>[b.id,b.topic])),additional_text:'',updated:Date.now(),save_key:crypto.randomUUID()});
  }
  function change(fields:Partial<Draft>){if(draft)persist({...draft,...fields,updated:Date.now(),save_key:crypto.randomUUID()})}
  async function resolve(action:string,target_id?:string){
    setBusy(true);setError('');
    const body=JSON.stringify({action,expected_version:draft?.expected_version??editing.version,base_id:draft?.base_id??revision.id,
      ...(action==='save'&&draft?{passages:Object.entries(draft.passages).map(([id,text])=>({id,text})),topics:Object.entries(draft.topics).map(([id,text])=>({id,text})),additional_text:draft.additional_text}:{}),
      ...(['keep','merge','replace'].includes(action)?{proposal_id:editing.proposal?.id,block_ids:chosen}:{}),
      ...(target_id?{target_id}:{})});
    if(command.current?.body!==body)command.current={body,key:action==='save'&&draft?draft.save_key:crypto.randomUUID()};
    try{
      await pending.current.catch(()=>{});
      const response=await fetch(path+'/edits',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':command.current.key},body});
      if(response.status===401){onExpired();throw new Error('The workspace is locked.')}
      const data=await response.json();
      if(!response.ok)throw new Error(data?.error?.message??'The save failed. Your draft remains available for retry.');
      command.current=null;
      if(draft){await deleteDraft(draft.id);setDraft(null);setRecoverable(await drafts(lecture))}
      setCompare(false);setHistory(null);setMessage('Your selected revision is saved.');onSaved(data);
    }catch(err){setError(err instanceof Error?err.message:'Could not save the notes.')}
    finally{if(mounted.current)setBusy(false)}
  }
  async function openHistory(){
    setError('');
    try{
      const response=await fetch(path+'/history',{cache:'no-store'});
      if(response.status===401)onExpired();
      if(!response.ok)throw new Error('Revision history is unavailable.');
      setHistory(await response.json());
    }catch(err){setError(err instanceof Error?err.message:'History is unavailable.')}
  }
  async function discard(){
    if(!draft)return;
    try{await pending.current.catch(()=>{});await deleteDraft(draft.id);setDraft(null);setMessage('Draft discarded. Saved notes are unchanged.');setRecoverable(await drafts(lecture))}
    catch{setError('The local draft could not be removed.')}
  }
  const staleDraft=!!draft&&(draft.base_id!==revision.id||draft.expected_version!==editing.version);
  return <section className="note-editing" aria-label="Edit and regenerate notes">
    <div className="editor-actions"><button className="secondary" disabled={busy||!!draft} onClick={start}>Edit notes</button><button className="text-button" disabled={busy||!!draft} onClick={()=>void openHistory()}>Revision history and undo</button></div>
    {message&&<p className="small" role="status">{message}</p>}{error&&<p className="error" role="alert">{error}</p>}
    {editing.sources_changed&&<p className="inline-notice">Sources or note preferences changed since this student revision. Your changes and original source links are preserved.</p>}
    {!draft&&recoverable.length>0&&<div className="inline-notice"><p>Unsaved drafts are available on this device.</p>{recoverable.map(item=><div key={item.id}><button className="text-button" onClick={()=>{persist({...item,id:crypto.randomUUID(),save_key:crypto.randomUUID(),updated:Date.now()});}}>Restore draft from {new Date(item.updated).toLocaleString()}</button><button className="text-button" onClick={()=>void deleteDraft(item.id).then(()=>drafts(lecture)).then(setRecoverable).catch(()=>setError('The draft could not be removed.'))}>Delete this local draft</button></div>)}</div>}
    {draft&&<div className="note-draft"><h3>Your draft</h3><p className="small">Changes are yours; existing source links remain for review. Code and equation line breaks are preserved.</p>
      {staleDraft&&<div className="inline-notice"><p>The saved copy changed. Compare your draft with the saved copy below. Transferring keeps your edited passages, including conflicts; untouched passages use the latest saved wording.</p><button className="secondary" onClick={()=>{
        const paragraphs=Object.fromEntries(revision.content.blocks.flatMap(b=>b.passages.map(p=>[p.id,p.text])));
        const topics=Object.fromEntries(revision.content.blocks.map(b=>[b.id,b.topic]));
        const changed=Object.entries(draft.passages).filter(([id,text])=>draft.base_passages?.[id]!==text);
        const changedTopics=Object.entries(draft.topics).filter(([id,text])=>draft.base_topics?.[id]!==text);
        const unmatched=changed.filter(([id])=>!(id in paragraphs)).map(([,text])=>text);
        change({base_id:revision.id,expected_version:editing.version,base_passages:paragraphs,base_topics:topics,
          passages:{...paragraphs,...Object.fromEntries(changed.filter(([id])=>id in paragraphs))},
          topics:{...topics,...Object.fromEntries(changedTopics.filter(([id])=>id in topics))},additional_text:[draft.additional_text,...unmatched].filter(Boolean).join('\n\n')});
      }}>Keep my edited passages on this saved copy</button></div>}
      {Object.entries(draft.topics).map(([id,text])=><label key={id}>Section heading<input value={text} maxLength={200} disabled={busy} onChange={e=>change({topics:{...draft.topics,[id]:e.target.value}})}/></label>)}
      {Object.entries(draft.passages).map(([id,text],index)=><label key={id}>Passage {index+1}<textarea aria-label={`Passage ${index+1}`} value={text} maxLength={12000} rows={5} disabled={busy} onChange={e=>change({passages:{...draft.passages,[id]:e.target.value}})}/></label>)}
      <label>My additional notes<textarea value={draft.additional_text} maxLength={12000} rows={4} disabled={busy} onChange={e=>change({additional_text:e.target.value})}/></label>
      <div className="editor-actions"><button className="primary" disabled={busy} onClick={()=>void resolve('save')}>{staleDraft?'Retry saving my changes':'Save my changes'}</button><button className="secondary" disabled={busy} onClick={()=>void discard()}>Discard local draft</button></div>
    </div>}
    {editing.proposal&&<div className="note-proposal"><h3>Regenerated suggestion</h3><p>Your saved student revision stays selected until you choose what to keep.</p>
      <button className="secondary" onClick={()=>setCompare(v=>!v)}>{compare?'Close comparison':'Compare suggestion'}</button>
      {compare&&<><div className="note-comparison"><div><h4>Current saved notes</h4>{revision.content.blocks.map(b=><section key={b.id}><h5>{b.topic}</h5>{b.passages.map(p=><pre className="comparison-text" key={p.id}>{p.text}</pre>)}</section>)}</div><div><h4>Suggested notes</h4>{editing.proposal.content.blocks.map(b=><section key={b.id}><label><input type="checkbox" checked={chosen.includes(b.id)} onChange={e=>setChosen(e.target.checked?[...chosen,b.id]:chosen.filter(id=>id!==b.id))}/> Include {b.topic} when merging</label>{b.passages.map(p=><pre className="comparison-text" key={p.id}>{p.text}</pre>)}</section>)}</div></div>
        {!editing.proposal_valid&&<p className="error">This suggestion is outdated. Apply your preferences to generate an updated suggestion.</p>}
        {draft&&<p>Save or discard your draft before resolving the suggestion.</p>}
        <p className="small">Merge appends checked sections to your current notes. Replace selects the full suggestion. Every choice can be undone from revision history.</p>
        <div className="editor-actions"><button disabled={busy||!!draft||!editing.proposal_valid} onClick={()=>void resolve('keep')}>Keep my notes</button><button disabled={busy||!!draft||!editing.proposal_valid||chosen.length===0} onClick={()=>void resolve('merge')}>Merge selected sections</button><button disabled={busy||!!draft||!editing.proposal_valid} onClick={()=>void resolve('replace')}>Replace with suggestion</button></div></>}
    </div>}
    {history&&<div className="note-history"><h3>Restore an earlier revision</h3><p>Restoring creates a new student revision. Earlier copies remain available.</p>{history.edits.map(h=><button className="text-button" key={h.id} disabled={busy||h.id===revision.id||!!draft} onClick={()=>void resolve('undo',h.id)}>Restore student revision {h.version} ({h.action})</button>)}{history.generated.map(h=><button className="text-button" key={h.id} disabled={busy||!!draft} onClick={()=>void resolve('undo',h.id)}>Restore generated revision {h.version}</button>)}<button className="text-button" onClick={()=>setHistory(null)}>Close history</button></div>}
  </section>;
}
