'use client';
import {useRef,useState} from 'react';

export type Quality={support:number;answerability:number;clarity:number;usefulness:number};
export type Question={id:string;kind:string;objective:string;question:string;answer:string;citations:{source_id:string;quote:string}[];version:number;revision_id:string;student_edited:boolean;quality:Quality;feedback:string;review:{version:number;rating:string}};
const blankQuality:Quality={support:-1,answerability:-1,clarity:-1,usefulness:-1};
const rubric:{key:keyof Quality;label:string;help:string}[]=[
  {key:'support',label:'Source support',help:'Are every answer claim, condition and worked step supported by the cited evidence?'},
  {key:'answerability',label:'Answerability',help:'Can the question be answered fully from the provided material, without unseen visuals or outside knowledge?'},
  {key:'clarity',label:'Clarity',help:'Is the wording specific, unambiguous and free of answer giveaways?'},
  {key:'usefulness',label:'Study usefulness',help:'Does it test an important idea or skill at a useful level, without redundant questions?'}];

export default function QuestionCard({initial,endpoint,csrf,stale,sources,onSaved}:{initial:Question;endpoint:string;csrf:string;stale:boolean;sources:{id:string;text:string;label?:string;segment_number?:number;start_sample?:number;sample_rate?:number}[];onSaved:(question:Question)=>void}){
  const [card,setCard]=useState(initial),[revealed,setRevealed]=useState(false),[scratch,setScratch]=useState('');
  const [question,setQuestion]=useState(initial.question),[answer,setAnswer]=useState(initial.answer),[quality,setQuality]=useState(initial.quality),[feedback,setFeedback]=useState(initial.feedback);
  const [base,setBase]=useState(initial.version),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [comparison,setComparison]=useState<Question|null>(null),[history,setHistory]=useState<Question[]>([]),[blocked,setBlocked]=useState(false),[retry,setRetry]=useState(false);
  const pending=useRef<{action:string;key:string;body:unknown}|null>(null);
  const needsWork=Object.values(card.quality).some(value=>value===0||value===1);
  async function command(action:string,body:unknown){
    const work=pending.current??{action,key:crypto.randomUUID(),body};pending.current=work;setBusy(true);setError('');setNotice('');
    try{
      const response=await fetch(`${endpoint}/${work.action}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':work.key},body:JSON.stringify(work.body)});
      const data=await response.json();
      if(!response.ok){if(response.status<500){pending.current=null;setRetry(false);if(response.status===409)setBlocked(true);}throw new Error(data.error?.message||'Could not save.');}
      pending.current=null;setRetry(false);
      if(work.action==='edits'){setCard(data);setBase(data.version);setQuestion(data.question);setAnswer(data.answer);setQuality(data.quality);setFeedback(data.feedback);setComparison(null);onSaved(data);}
      else{const updated={...card,review:data};setCard(updated);onSaved(updated);}
      setNotice(work.action==='edits'?'Question revision and quality review saved.':'Self-assessment saved.');
    }catch(e){setRetry(!!pending.current);setError(e instanceof Error?e.message:'Could not save.');}finally{setBusy(false);}
  }
  async function loadVersions(){
    setBusy(true);setError('');
    try{const response=await fetch(`${endpoint}/history`,{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Could not load saved versions.');setHistory(data);setComparison(data[0]);}
    catch(e){setError(e instanceof Error?e.message:'Could not load saved versions.');}finally{setBusy(false);}
  }
  function useSaved(saved:Question){setQuestion(saved.question);setAnswer(saved.answer);setQuality(saved.quality);setFeedback(saved.feedback);setBase(comparison?.version??card.version);setBlocked(false);setNotice('Version loaded into the editor. Save to append a new revision.');}
  return <article className="catchup-item learning-card"><p className="eyebrow">{card.kind} · {card.objective.replaceAll('_',' ')}</p><h4 className="study-text">{card.question}</h4>
    {card.student_edited&&<p className="small muted">Student-edited question or answer; citations are retained, not automatically revalidated for meaning.</p>}
    {needsWork&&<p className="inline-notice">Your quality review flags this question for improvement. Self-assessment is paused until the concerns are resolved.</p>}
    <label>Your practice answer (not saved)<textarea value={scratch} onChange={e=>setScratch(e.target.value)} rows={3}/></label>
    <button className="secondary" aria-expanded={revealed} onClick={()=>setRevealed(!revealed)}>{revealed?'Hide generated answer':'Reveal generated answer'}</button>
    {revealed&&<div><p className="study-text">{card.answer}</p><div className="study-sources">{card.citations.map((citation,index)=>{const source=sources.find(s=>s.id===citation.source_id);return <details key={index}><summary>{source?.label||`Evidence · recording ${source?.segment_number??'—'}, ${Math.floor((source?.start_sample??0)/(source?.sample_rate??1))}s`}</summary><blockquote className="study-text">{citation.quote}</blockquote><p className="study-text">{source?.text}</p></details>;})}</div>
      <p>Self-assessment: {card.review.rating}</p><div className="editor-actions">{[['again','Needs review'],['developing','Developing'],['confident','Confident'],['unreviewed','Reset self-assessment']].map(([rating,label])=><button key={rating} className="secondary" disabled={busy||retry||blocked||stale||(needsWork&&rating!=='unreviewed')} onClick={()=>void command('reviews',{question_revision:card.revision_id,expected_version:card.review.version,rating})}>{label}</button>)}</div>
    </div>}
    <details className="question-editor"><summary>Edit question and evaluate quality</summary>
      <p className="small muted">These are your quality judgments, separate from recall confidence and measured learning outcomes. Save retains prior versions. Editing or reviewing creates a new version with fresh self-assessments.</p>
      <fieldset disabled={busy||retry}><label>Question wording<textarea aria-label="Question wording" value={question} maxLength={2000} onChange={e=>{setQuestion(e.target.value);setQuality(blankQuality);}}/></label><label>Reference answer<textarea aria-label="Reference answer" rows={5} value={answer} maxLength={6000} onChange={e=>{setAnswer(e.target.value);setQuality(blankQuality);}}/></label>
        {rubric.map(item=><label className="question-rubric" key={item.key}>{item.label}<span className="small muted">{item.help}</span><select aria-label={item.label} value={quality[item.key]} onChange={e=>setQuality({...quality,[item.key]:Number(e.target.value)})}><option value={-1}>Not reviewed</option><option value={0}>0 — Fails</option><option value={1}>1 — Needs improvement</option><option value={2}>2 — Meets criterion</option></select></label>)}
        <label>Quality feedback<textarea value={feedback} maxLength={1000} onChange={e=>setFeedback(e.target.value)}/></label>
        <button className="primary" disabled={blocked||question.trim().length<8||answer.trim().length<8} onClick={()=>void command('edits',{expected_version:base,question,answer,quality,feedback})}>Save question revision</button>
        <button className="secondary" onClick={()=>void loadVersions()}>Load saved versions to compare</button>
      </fieldset>
      {comparison&&<section aria-label="Saved question comparison"><h4>Latest saved version {comparison.version}</h4><p className="study-text">{comparison.question}</p><p className="study-text">{comparison.answer}</p><p>Your draft remains above. Choose how to continue.</p><button className="secondary" disabled={busy||retry} onClick={()=>{setBase(comparison.version);setCard(comparison);setQuality(blankQuality);setBlocked(false);setNotice('Draft kept against the loaded version. Recheck quality, then save.');}}>Keep my draft against this version</button><button className="secondary" disabled={busy||retry} onClick={()=>useSaved(comparison)}>Use saved wording</button><details><summary>Earlier versions / undo</summary>{history.map(saved=><div key={saved.revision_id}><p>Version {saved.version}: {saved.question}</p><button className="text-button" disabled={busy||retry} onClick={()=>useSaved(saved)}>Load version {saved.version} into draft</button></div>)}</details></section>}
      <p className="small muted">Unsaved edits remain in this open editor during failures. Switching cards/sets, refreshing or leaving clears them.</p>
    </details>
    {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{retry&&<button disabled={busy} className="secondary" onClick={()=>void command('',{})}>Retry question save</button>}
  </article>;
}
