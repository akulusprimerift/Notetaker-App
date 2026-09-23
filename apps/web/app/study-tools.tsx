'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import CourseTerminology from './course-terminology';
import LearningTools from './learning-tools';
import GeneratedQuestions from './generated-questions';

type Mark={id:string;run_id:string;sample:number;sample_rate:number;recording_number:number;label:string;version:number;removed:boolean;awaiting_audio:boolean};
type Source={id:string;text:string;segment_number?:number;start_sample?:number;end_sample?:number;sample_rate?:number;audio_url?:string;label?:string;source_kind?:string};
type CatchUp={snapshot_id:string|null;revision_id:string|null;message:string;start_seconds?:number;end_seconds?:number;recording_number?:number;omitted_stale:number;issues:unknown[];more_available?:boolean;awaiting_transcript?:boolean;audio_removed?:boolean;items:{topic:string;text:string;student_edited:boolean;source_ids:string[];kind:string;passage_id:string}[];sources:Source[]};
const time=(seconds:number)=>`${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;

export default function StudyTools({lecture,course,csrf}:{lecture:string;course:string;csrf:string}){
  const [marks,setMarks]=useState<Mark[]>([]),[seconds,setSeconds]=useState('180'),[result,setResult]=useState<CatchUp|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[undo,setUndo]=useState<Mark|null>(null);
  const sequence=useRef(0);
  const load=useCallback(async()=>{const response=await fetch(`/api/lectures/${lecture}/study/marks`,{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Could not load important moments.');setMarks(data);},[lecture]);
  useEffect(()=>{void load().catch(e=>setError(e.message));const changed=()=>void load().catch(e=>setError(e.message));window.addEventListener('study-marks-changed',changed);return()=>{sequence.current++;window.removeEventListener('study-marks-changed',changed);};},[load]);
  async function catchUp(mark?:Mark){
    const ticket=++sequence.current;setBusy(true);setError('');
    const query=new URLSearchParams({seconds:mark?'60':seconds});
    if(mark){query.set('run_id',mark.run_id);query.set('end_sample',String(Math.max(1,mark.sample)));}
    try{const response=await fetch(`/api/lectures/${lecture}/study/catch-up?${query}`,{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Could not load catch-up.');if(ticket===sequence.current)setResult(data);}
    catch(e){if(ticket===sequence.current)setError(e instanceof Error?e.message:'Could not load catch-up.');}finally{if(ticket===sequence.current)setBusy(false);}
  }
  async function toggle(mark:Mark,removed:boolean){
    setBusy(true);setError('');
    try{const response=await fetch(`/api/lectures/${lecture}/study/marks/${mark.id}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({expected_version:mark.version,removed})});const row=await response.json();if(!response.ok)throw new Error(row.error?.message||'Could not update this marker.');setUndo(removed?row:null);await load();}
    catch(e){setError(e instanceof Error?e.message:'Could not update this marker.');await load().catch(()=>{});}finally{setBusy(false);}
  }
  return <section className="study-tools"><header><p className="eyebrow">YOUR STUDY COMPANION</p><h2>Pick up the thread.</h2><p className="muted">Revisit recent ideas and the moments you marked. Your detailed notes stay intact.</p></header>
    <div className="study-actions"><label>Recent interval<select value={seconds} onChange={e=>setSeconds(e.target.value)}><option value="60">Last minute</option><option value="180">Last 3 minutes</option><option value="300">Last 5 minutes</option><option value="600">Last 10 minutes</option></select></label><button className="primary" disabled={busy} onClick={()=>void catchUp()}>{busy?'Loading…':'Catch Me Up'}</button></div>
    <p className="small muted">Uses complete excerpts from saved notes, or transcript excerpts when notes are still catching up. No additional model request.</p>
    {error&&<p className="error" role="alert">{error}</p>}
    {result&&<section className="catchup-result" aria-label="Catch-up result"><h3>Recent discussion</h3><p role="status">{result.message}</p>{result.recording_number!==undefined&&<p className="small muted">Recording {result.recording_number} · {time(result.start_seconds??0)}–{time(result.end_seconds??0)} of saved transcript</p>}{(result.awaiting_transcript||result.issues.length>0||result.omitted_stale>0)&&<p className="inline-notice">{result.awaiting_transcript?'This moment is not fully transcribed yet. ':''}{result.issues.length>0?'The transcript has source warnings. ':''}{result.omitted_stale>0?'Passages linked to corrected or unavailable sources were omitted.':''}</p>}
      {result.items.map((item,index)=><article className="catchup-item" key={item.passage_id}><p className="eyebrow">{index===result.items.length-1?'LATEST SAVED IDEA':'EARLIER IN THIS INTERVAL'}</p><h3>{item.topic}</h3><p className="small muted">{item.kind==='transcript'?'Transcript excerpt':item.student_edited?'Your edited note · not AI-verified':'Saved note excerpt'}</p><p className="study-text">{item.text}</p><div className="study-sources">{item.source_ids.map(id=>{const source=result.sources.find(s=>s.id===id);return source?<details key={id}><summary>{source.source_kind?source.label:`Source · recording ${source.segment_number}, ${time((source.start_sample??0)/(source.sample_rate??1))}`}</summary><p className="study-text">{source.text}</p>{source.audio_url&&!result.audio_removed&&<audio controls preload="none" src={source.audio_url}/>}</details>:null;})}</div></article>)}
      {result.more_available&&<p className="small muted">More content is available in Study notes and Transcript.</p>}<p className="small muted">This view stays still while you read. Press Catch Me Up again for newer saved content.</p></section>}
    <section className="important-moments"><div className="section-row"><h3>Important to you</h3><button className="text-button" disabled={busy} onClick={()=>void load().catch(e=>setError(e.message))}>Refresh markers</button></div><p className="small muted">These are your bookmarks, not claims of professor emphasis. These previously saved bookmarks remain available. New important ideas are highlighted automatically in your notes.</p>{marks.filter(m=>!m.removed).length===0&&<p>No important moments marked yet.</p>}{marks.filter(m=>!m.removed).map(mark=><article className="important-moment" key={mark.id}><div><strong>★ {mark.label}</strong><p className="small muted">Recording {mark.recording_number} · {time(mark.sample/mark.sample_rate)}{mark.awaiting_audio?' · audio not yet confirmed here':''}</p></div><div className="editor-actions"><button className="secondary" disabled={busy} onClick={()=>void catchUp(mark)}>Review this moment</button><button className="text-button" disabled={busy} onClick={()=>void toggle(mark,true)}>Remove marker</button></div></article>)}{undo&&<button className="secondary" disabled={busy} onClick={()=>void toggle(undo,false)}>Undo marker removal</button>}</section>
    <LearningTools key={lecture} lecture={lecture} csrf={csrf}/>
    <GeneratedQuestions key={`questions:${lecture}`} lecture={lecture} csrf={csrf}/>
    <CourseTerminology key={course} course={course} csrf={csrf}/>
  </section>;
}
