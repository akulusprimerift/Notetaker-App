'use client';
import {useCallback,useEffect,useId,useState} from 'react';

type Terms={version:number;terms:string[]};
export default function CourseTerminology({course,csrf}:{course:string;csrf:string}){
  const id=useId();
  const [saved,setSaved]=useState<Terms|null>(null),[draft,setDraft]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const load=useCallback(async(initial=false)=>{
    const response=await fetch(`/api/courses/${course}/terminology`,{cache:'no-store'});const data=await response.json();
    if(!response.ok)throw new Error(data.error?.message||'Could not load course terms.');
    setSaved(data);if(initial)setDraft(data.terms.join('\n'));else setNotice('Saved terms loaded below. Your draft has been kept.');
  },[course]);
  useEffect(()=>{void load(true).catch(e=>setError(e.message));},[load]);
  async function save(){
    if(!saved)return;setBusy(true);setError('');setNotice('');
    try{
      const response=await fetch(`/api/courses/${course}/terminology`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({expected_version:saved.version,terms:draft.split('\n').map(s=>s.trim()).filter(Boolean)})});const data=await response.json();
      if(!response.ok)throw new Error(data.error?.message||'Could not save terms. Use up to 40 unique terms, 60 characters per term and 1,000 characters total.');
      setSaved(data);setDraft(data.terms.join('\n'));setNotice('Course terms saved for future transcription batches.');
    }catch(e){setError(e instanceof Error?e.message:'Could not save course terms.');}finally{setBusy(false);}
  }
  return <section className="course-terminology"><p className="eyebrow">HELP WITH SPECIALIST WORDS</p><h3>Course terminology</h3><p className="muted">Add names and technical terms for every lecture in this course. These spelling hints apply to future transcription batches. Earlier transcripts and your corrections stay unchanged.</p><label htmlFor={id}>Terms, one per line</label><textarea id={id} rows={5} maxLength={1100} value={draft} disabled={busy||!saved} onChange={e=>setDraft(e.target.value)} placeholder={'e.g.\nmitochondria\noxidative phosphorylation'}/><p className="small muted">Up to 40 unique terms · 60 characters each · 1,000 characters total. Hints can help recognition, but do not prove a term was spoken. Review the transcript for accuracy.</p><div className="editor-actions"><button className="primary" disabled={busy||!saved} onClick={()=>void save()}>{busy?'Saving…':'Save course terms'}</button><button className="text-button" disabled={busy} onClick={()=>void load(!saved).catch(e=>setError(e.message))}>Load saved terms</button></div>{error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{saved&&saved.terms.join('\n')!==draft&&<details><summary>Compare saved terms (version {saved.version})</summary><pre className="study-text">{saved.terms.join('\n')||'No saved terms.'}</pre><button className="secondary" disabled={busy} onClick={()=>setDraft(saved.terms.join('\n'))}>Use saved terms instead of my draft</button></details>}</section>;
}
