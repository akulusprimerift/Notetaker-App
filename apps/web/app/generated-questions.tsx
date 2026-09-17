'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import QuestionCard,{Question} from './question-card';

type Summary={id:string;topic:string;model:string;status:string;error_code:string|null;preview:string;created_at:string;count:number};
type Inventory={revision_id:string|null;blocks:{id:string;topic:string}[];preference_id:string|null;model:string|null;enabled:boolean;cloud:boolean;sets:Summary[]};
type SavedSet=Summary&{revision_id:string;stale:boolean;questions:Question[];sources:{id:string;text:string;label?:string;segment_number?:number;start_sample?:number;sample_rate?:number}[];issues:unknown[]};

export default function GeneratedQuestions({lecture,csrf}:{lecture:string;csrf:string}){
  const endpoint=`/api/lectures/${lecture}/study/questions`;
  const [inventory,setInventory]=useState<Inventory|null>(null),[selected,setSelected]=useState(''),[saved,setSaved]=useState<SavedSet|null>(null);
  const [block,setBlock]=useState(''),[kind,setKind]=useState('mixed'),[count,setCount]=useState(4),[focus,setFocus]=useState(''),[consent,setConsent]=useState(false);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[retry,setRetry]=useState(false),[cardIndex,setCardIndex]=useState(0),[refresh,setRefresh]=useState(0);
  const pending=useRef<{key:string;url:string;body:unknown}|null>(null);
  const loadInventory=useCallback(async(signal?:AbortSignal)=>{const response=await fetch(endpoint,{cache:'no-store',signal});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Could not load question setup.');if(!signal?.aborted){setInventory(data);setSelected(value=>value||data.sets[0]?.id||'');}return data as Inventory;},[endpoint]);
  useEffect(()=>{const controller=new AbortController();void loadInventory(controller.signal).catch(e=>{if(!controller.signal.aborted)setError(e.message);});return()=>controller.abort();},[loadInventory,refresh]);
  const activeId=selected||inventory?.sets[0]?.id||'';
  useEffect(()=>{
    if(!activeId)return;
    const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
    const load=async()=>{try{const response=await fetch(`${endpoint}/${activeId}`,{cache:'no-store',signal:controller.signal});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Could not load question set.');if(controller.signal.aborted)return;setSaved(data);if(data.status==='due'||data.status==='running'){timer=setTimeout(()=>void load(),2000);}else{void loadInventory(controller.signal).catch(()=>{});}}
      catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Could not load questions.');}};
    void load();return()=>{controller.abort();clearTimeout(timer);};
  },[endpoint,activeId,refresh,loadInventory]);
  async function command(url:string,body:unknown){
    const work=pending.current??{key:crypto.randomUUID(),url,body};pending.current=work;setBusy(true);setError('');
    try{const response=await fetch(work.url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':work.key},body:JSON.stringify(work.body)});const data=await response.json();if(!response.ok){if(response.status<500){pending.current=null;setRetry(false);}throw new Error(data.error?.message||'Question request failed.');}pending.current=null;setRetry(false);setSelected(data.id);setSaved(null);setCardIndex(0);setConsent(false);setRefresh(value=>value+1);}
    catch(e){setRetry(!!pending.current);setError(e instanceof Error?e.message:'Question request failed.');}finally{setBusy(false);}
  }
  const chosen=inventory?.blocks.find(b=>b.id===block)?.id||inventory?.blocks[0]?.id||'';
  const shown=saved?.id===activeId?saved:null;
  const index=Math.min(cardIndex,Math.max(0,(shown?.questions.length??0)-1)),card=shown?.questions[index];
  const reviewed=shown?.questions.filter(q=>Object.values(q.quality).every(value=>value>=0)).length??0;
  const needsWork=shown?.questions.filter(q=>Object.values(q.quality).some(value=>value===0||value===1)).length??0;
  return <section className="learning-tools" aria-label="Generated questions"><h3>Generated questions & flashcards</h3><p>Create focused questions from one saved note section using your selected model. Every new set is saved separately; earlier sets and edits remain available.</p>
    <p className="small muted">Citations are checked for exact source text. This does not establish answer correctness or learning benefit. Use the quality rubric before relying on a set.</p>
    <fieldset disabled={busy||retry}><div className="study-actions"><label>Source section<select value={chosen} onChange={e=>setBlock(e.target.value)}>{inventory?.blocks.map(b=><option key={b.id} value={b.id}>{b.topic}</option>)}</select></label><label>Question format<select value={kind} onChange={e=>setKind(e.target.value)}><option value="mixed">Mixed</option><option value="flashcard">Flashcards</option><option value="practice">Practice questions</option></select></label><label>Maximum questions<input type="number" min={1} max={8} value={count} onChange={e=>setCount(Number(e.target.value))}/></label></div>
      <label>Study focus (optional)<input className="question-focus" value={focus} maxLength={500} onChange={e=>setFocus(e.target.value)} placeholder="For example: prerequisites and worked steps"/></label>
      <p>Model: {inventory?.model||'Choose a model in Note preferences'}</p>
      {inventory?.cloud&&<label className="question-consent"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/> <span>Send this section, source text and study focus to {inventory.model} for question generation.</span></label>}
      <button className="primary" disabled={!chosen||!inventory?.enabled||!inventory?.preference_id||!Number.isInteger(count)||count<1||count>8||(inventory?.cloud&&!consent)||inventory?.sets.some(s=>s.status==='due'||s.status==='running')} onClick={()=>void command(endpoint,{revision_id:inventory?.revision_id,block_id:chosen,preference_id:inventory?.preference_id,kind,count,focus,cloud_consent:consent})}>Generate new question set</button>
    </fieldset>
    {!chosen&&<p>Save current source-linked notes before generating questions.</p>}
    <div className="study-actions"><label>Saved question set<select value={activeId} onChange={e=>{setSelected(e.target.value);setSaved(null);setCardIndex(0);}}>{inventory?.sets.map((s,i)=><option key={s.id} value={s.id}>{i+1}. {s.topic} · {s.status} · {new Date(s.created_at).toLocaleString()}</option>)}</select></label><button className="secondary" disabled={busy||retry} onClick={()=>{setError('');setConsent(false);setRefresh(value=>value+1);}}>Refresh question setup and set</button></div>
    <p className="small muted">Changing cards/sets, refreshing or leaving clears scratch answers and unsaved question edits. Saved versions remain.</p>
    {error&&<p role="alert" className="error">{error}</p>}{retry&&<button className="secondary" disabled={busy} onClick={()=>void command('',{})}>Retry question request</button>}
    {shown&&<><p role="status">Question set: {shown.status}{shown.error_code?` · ${shown.error_code.replaceAll('_',' ')}`:''}</p>
      {(shown.status==='due'||shown.status==='running')&&<><p>Queued behind note work. Audio capture continues independently.</p><button className="secondary" disabled={busy||retry} onClick={()=>void command(`${endpoint}/${shown.id}/cancel`,{})}>Cancel question generation</button>{shown.preview&&<details open><summary>Unvalidated generation preview — not saved questions</summary><p className="study-text">{shown.preview}</p></details>}</>}
      {(shown.status==='failed'||shown.status==='cancelled')&&<p>Earlier saved sets are intact. Refresh setup and generate a new set when ready.</p>}
      {shown.stale&&<p className="inline-notice">This set uses an earlier note revision or changed sources. Inspect its pinned evidence; generate a new set for current practice. Self-assessment is disabled.</p>}
      {!!shown.issues.length&&<p className="inline-notice">The input notes or transcript have source warnings. Review them before studying these questions.</p>}
      {!!shown.questions.length&&<><p>Quality reviewed: {reviewed}/{shown.questions.length} · Needs improvement: {needsWork}. These are your reviews, not measured learning outcomes.</p><div className="editor-actions"><button className="secondary" disabled={index===0} onClick={()=>setCardIndex(index-1)}>Previous generated question</button><span>Question {index+1} of {shown.questions.length}</span><button className="secondary" disabled={index===shown.questions.length-1} onClick={()=>setCardIndex(index+1)}>Next generated question</button></div></>}
      {card&&<QuestionCard key={`${shown.id}:${card.id}:${refresh}`} initial={card} endpoint={`${endpoint}/${shown.id}/${card.id}`} csrf={csrf} stale={shown.stale} sources={shown.sources} onSaved={updated=>setSaved(current=>current?{...current,questions:current.questions.map(q=>q.id===updated.id?updated:q)}:current)}/>}
      <details className="small muted"><summary>Generation provenance</summary><p className="study-text">Saved note revision: {shown.revision_id}</p><p>Model: {shown.model} · Fewer questions may be returned when the evidence is limited.</p></details>
    </>}
  </section>;
}
