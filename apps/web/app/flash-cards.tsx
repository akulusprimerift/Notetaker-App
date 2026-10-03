'use client';
import {FormEvent, useCallback, useEffect, useRef, useState} from 'react';
import QuestionCard,{Question} from './question-card';

type SetSummary={id:string;topic:string;prompt:string;model:string;status:string;error_code:string|null;preview:string;created_at:string;count:number};
type Inventory={revision_id:string|null;has_notes:boolean;omitted_blocks:number;preference_id:string|null;model:string|null;enabled:boolean;cloud:boolean;sets:SetSummary[]};
type Source={id:string;text:string;label?:string;segment_number?:number;start_sample?:number;end_sample?:number;sample_rate?:number};
type SavedSet=SetSummary&{revision_id:string;stale:boolean;questions:Question[];sources:Source[];issues:unknown[];metadata:Record<string,unknown>;quality_counts:{reviewed:number;needs_work:number;total:number}};
type Generation={key:string;body:{revision_id:string;preference_id:string;prompt:string;cloud_consent:boolean}};

export default function FlashCards({lecture,csrf}:{lecture:string;csrf:string}){
  const endpoint=`/api/lectures/${encodeURIComponent(lecture)}/study/questions`;
  const [inventory,setInventory]=useState<Inventory|null>(null),[selected,setSelected]=useState(''),[saved,setSaved]=useState<SavedSet|null>(null);
  const [loading,setLoading]=useState(true),[detailLoading,setDetailLoading]=useState(false),[loadError,setLoadError]=useState(''),[detailError,setDetailError]=useState('');
  const [dialogError,setDialogError]=useState(''),[busy,setBusy]=useState(false),[retry,setRetry]=useState(false);
  const [prompt,setPrompt]=useState(''),[consent,setConsent]=useState(false),[cardIndex,setCardIndex]=useState(0),[refresh,setRefresh]=useState(0);
  const dialog=useRef<HTMLDialogElement>(null),pending=useRef<Generation|null>(null);

  const loadInventory=useCallback(async(signal?:AbortSignal)=>{
    const response=await fetch(endpoint,{cache:'no-store',signal});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error?.message||'Could not load saved flash cards.');
    if(!signal?.aborted){
      setInventory(data);
      setSelected(current=>data.sets.some((row:SetSummary)=>row.id===current)?current:(data.sets[0]?.id||''));
    }
    return data as Inventory;
  },[endpoint]);

  useEffect(()=>{
    const controller=new AbortController();setLoading(true);setLoadError('');
    void loadInventory(controller.signal).catch(error=>{if(!controller.signal.aborted)setLoadError(error instanceof Error?error.message:'Could not load saved flash cards.');})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[loadInventory,refresh]);

  const activeId=selected||inventory?.sets[0]?.id||'';
  useEffect(()=>{
    if(!activeId){setSaved(null);setDetailLoading(false);setDetailError('');return;}
    const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
    setSaved(null);setDetailLoading(true);setDetailError('');
    const read=async()=>{
      try{
        const response=await fetch(`${endpoint}/${encodeURIComponent(activeId)}`,{cache:'no-store',signal:controller.signal});
        const data=await response.json();
        if(!response.ok)throw new Error(data.error?.message||'Could not load this flash card set.');
        if(controller.signal.aborted)return;
        setSaved(data);setDetailLoading(false);
        if(data.status==='due'||data.status==='running')timer=setTimeout(()=>void read(),1500);
        else if(data.status==='completed')void loadInventory(controller.signal).catch(()=>{});
      }catch(error){if(!controller.signal.aborted){setDetailLoading(false);setDetailError(error instanceof Error?error.message:'Could not load this flash card set.');}}
    };
    void read();return()=>{controller.abort();clearTimeout(timer);};
  },[endpoint,activeId,refresh,loadInventory]);

  async function generate(event?:FormEvent){
    event?.preventDefault();
    const body=pending.current?.body??{
      revision_id:inventory?.revision_id||'',preference_id:inventory?.preference_id||'',
      prompt:prompt.trim(),cloud_consent:consent,
    };
    if(!body.prompt||!body.revision_id||!body.preference_id)return;
    const work=pending.current??{key:crypto.randomUUID(),body};pending.current=work;
    setBusy(true);setDialogError('');
    try{
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':work.key},body:JSON.stringify(work.body)});
      const data=await response.json();
      if(!response.ok){if(response.status<500){pending.current=null;setRetry(false);}throw new Error(data.error?.message||'Flash card generation could not be queued.');}
      pending.current=null;setRetry(false);setPrompt(work.body.prompt);setConsent(false);setDialogError('');
      if(dialog.current?.open)dialog.current.close();
      setSelected(data.id);setSaved(null);setCardIndex(0);setRefresh(value=>value+1);
    }catch(error){
      setRetry(!!pending.current);setDialogError(error instanceof Error?error.message:'Flash card generation could not be queued.');
    }finally{setBusy(false);}
  }

  function openDialog(value=prompt){
    setPrompt(pending.current?.body.prompt??value);setConsent(pending.current?.body.cloud_consent??false);setDialogError('');
    if(!dialog.current?.open)dialog.current?.showModal();
  }

  const shown=saved?.id===activeId?saved:null;
  // Older saved question sets remain readable; new requests are constrained to flashcards.
  const cards=shown?.questions??[];
  const index=Math.min(cardIndex,Math.max(0,cards.length-1));
  const card=cards[index];
  const pendingJob=inventory?.sets.some(row=>row.status==='due'||row.status==='running')??false;
  const canGenerate=!!inventory?.has_notes&&!!inventory.preference_id&&inventory.enabled&&!pendingJob&&!loading&&!busy;

  return <section className="flash-cards" aria-label="Flash cards" aria-busy={loading||detailLoading||busy}>
    <header className="flash-cards-heading">
      <div><p className="eyebrow">STUDY FROM YOUR NOTES</p><h2>Flash cards</h2><p className="muted">Give an instruction. Cards use your current saved notes and keep their source links.</p></div>
      <button className="primary" disabled={!canGenerate} onClick={()=>openDialog()}>{retry?'Continue pending request':'Create flash cards'}</button>
    </header>
    <p className="flash-card-model">Selected model: <strong>{inventory?.model||'Choose a model in Note preferences'}</strong></p>
    {loading&&<p role="status" aria-live="polite">Loading saved flash cards…</p>}
    {loadError&&<div className="flash-card-error"><p role="alert" className="error">{loadError}</p><button className="secondary" onClick={()=>setRefresh(value=>value+1)}>Retry loading</button></div>}
    {!loading&&!loadError&&inventory&&!inventory.has_notes&&<p className="flash-card-empty">{inventory.omitted_blocks?'Saved notes are not currently source-linked enough to make flash cards. Review or refresh the notes to restore their evidence links.':'Save source-linked notes before creating flash cards.'}</p>}
    {!loading&&!loadError&&inventory?.has_notes&&!inventory.enabled&&<p className="flash-card-empty">Choose and enable a note model in Note preferences before creating flash cards.</p>}
    {!loading&&!loadError&&inventory?.has_notes&&inventory.enabled&&inventory.sets.length===0&&<div className="flash-card-empty"><h3>No flash cards yet</h3><p>Your notes are ready. Add instructions when you want to make a set.</p><button className="secondary" onClick={()=>openDialog()}>Write instructions</button></div>}
    {inventory&&inventory.sets.length>1&&<label className="flash-card-set-picker">Saved set
      <select value={activeId} onChange={event=>{setSelected(event.target.value);setCardIndex(0);}}>
        {inventory.sets.map((row,index)=>{const date=new Date(row.created_at).toLocaleString();return <option key={row.id} value={row.id}>{index===0?'Latest':'Earlier'} · {date} · {row.status}</option>;})}
      </select>
    </label>}
    {detailLoading&&<p role="status" aria-live="polite">Loading this saved set…</p>}
    {detailError&&<div className="flash-card-error"><p role="alert" className="error">{detailError}</p><button className="secondary" onClick={()=>setRefresh(value=>value+1)}>Retry loading this set</button></div>}
    {shown&&<>
      {(shown.status==='due'||shown.status==='running')&&<div className="flash-card-progress"><p role="status" aria-live="polite">Generating flash cards with {shown.model}…</p><p className="small muted">The request uses saved notes from revision {shown.revision_id}. Recording and note updates continue independently.</p>
        {shown.preview&&<details><summary>Unvalidated generation preview</summary><p className="study-text">{shown.preview}</p></details>}
      </div>}
      {shown.status==='failed'&&<div className="flash-card-error"><p role="alert" className="error">These flash cards could not be generated{shown.error_code?` (${shown.error_code.replaceAll('_',' ')})`:''}. Your notes and earlier saved sets are intact.</p><button className="secondary" onClick={()=>openDialog(shown.prompt)}>Try again</button></div>}
      {shown.status==='cancelled'&&<div className="flash-card-error"><p role="status">This generation was cancelled. Your notes and earlier saved sets are intact.</p><button className="secondary" onClick={()=>openDialog(shown.prompt)}>Try again</button></div>}
      {shown.status==='completed'&&shown.stale&&<p className="inline-notice">This set uses an earlier saved note revision. Its pinned sources remain available; generate a new set for the current notes.</p>}
      {shown.status==='completed'&&!!shown.issues.length&&<p className="inline-notice">The saved notes or transcript include source warnings. Review them before relying on these cards.</p>}
      {shown.status==='completed'&&!cards.length&&<p className="flash-card-empty">This saved set has no flash cards. Earlier saved study sets remain unchanged.</p>}
      {shown.status==='completed'&&!!cards.length&&<>
        <div className="flash-card-navigation"><button className="secondary" disabled={index===0} onClick={()=>setCardIndex(index-1)}>Previous card</button><span aria-live="polite">Card {index+1} of {cards.length}</span><button className="secondary" disabled={index===cards.length-1} onClick={()=>setCardIndex(index+1)}>Next card</button></div>
        {card&&<QuestionCard key={`${shown.id}:${card.id}:${refresh}`} initial={card} endpoint={`${endpoint}/${shown.id}/${card.id}`} csrf={csrf} stale={shown.stale} sources={shown.sources} onSaved={updated=>setSaved(current=>current?{...current,questions:current.questions.map(question=>question.id===updated.id?updated:question)}:current)}/>}
        <details className="flash-card-provenance"><summary>Instructions and sources</summary><p className="study-text">{shown.prompt}</p><p>Saved note revision: {shown.revision_id}</p><p>Model: {shown.model}</p><p>{cards.length} saved flash card{cards.length===1?'':'s'} · Source quotes are retained with each card.</p></details>
      </>}
    </>}
    <dialog ref={dialog} className="flash-card-dialog" aria-labelledby="flash-card-dialog-title" onClose={()=>setDialogError('')}>
      <form onSubmit={event=>void generate(event)}>
        <p className="eyebrow">YOUR NOTES, YOUR INSTRUCTIONS</p><h3 id="flash-card-dialog-title">Create flash cards</h3>
        <p id="flash-card-dialog-help" className="muted">Your request is sent with the current saved note passages and their source text. Up to eight supported cards are saved as a new set.</p>
        <label htmlFor="flash-card-prompt">What should the cards help you study?</label>
        <textarea id="flash-card-prompt" required minLength={1} maxLength={2000} rows={6} value={prompt} onChange={event=>setPrompt(event.target.value)} aria-describedby="flash-card-dialog-help" placeholder="For example: Make concise cards for each key idea, including the conditions and exceptions." disabled={busy||retry}/>
        {inventory?.cloud&&<label className="question-consent"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)} disabled={busy||retry}/> <span>Send these saved notes, source text and instructions to {inventory.model}.</span></label>}
        {dialogError&&<p role="alert" className="error">{dialogError}</p>}
        {retry&&<button type="button" className="secondary" disabled={busy} onClick={()=>void generate()}>Retry sending the same request</button>}
        <div className="flash-card-dialog-actions"><button type="button" className="secondary" disabled={busy} onClick={()=>dialog.current?.close()}>Cancel</button><button type="submit" className="primary" disabled={!prompt.trim()||!inventory?.has_notes||!inventory?.revision_id||!inventory?.preference_id||!inventory.enabled||busy||retry||(!!inventory.cloud&&!consent)}>{busy?'Sending…':'Generate flash cards'}</button></div>
      </form>
    </dialog>
  </section>;
}
