'use client';
import {useCallback,useEffect,useRef,useState} from 'react';

type Passage={id:string;segment_id:string;revision:number;text:string;author:string;segment_number:number;sample_rate:number;start_sample:number;end_sample:number;confidence:{value:number|null};audio_url:string};
type State={status:string;counts:Record<string,number>;errors:string[];waiting_for_audio:boolean;snapshot:{id:string;sequence:number;segments:Passage[];issues:{reason:string}[]}|null};
type Draft={segment:string;base:string;text:string;key:string};
class TranscriptError extends Error {constructor(message:string,public status:number){super(message);}}
const stamp=(sample:number,rate:number)=>{const s=Math.floor(sample/rate);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');};
const statuses:Record<string,string>={not_started:'No saved speech yet',awaiting_saved_audio:'Waiting for recording to finish saving',queued:'Waiting for local transcription',processing:'Transcribing saved audio',needs_attention:'Transcription needs attention',processed:'Saved audio processed'};
async function api<T>(path:string,init:RequestInit={}):Promise<T>{
  const response=await fetch(path,{cache:'no-store',...init,headers:{'Content-Type':'application/json',...init.headers}});
  const data=await response.json().catch(()=>null);
  if(!response.ok)throw new TranscriptError(data?.error?.message??'The transcript could not be reached. Your draft stays here.',response.status);
  return data;
}
export default function Transcript({owner,lecture,csrf,onBusy,onSessionExpired}:{owner:string;lecture:string;csrf:string;onBusy:(value:boolean)=>void;onSessionExpired:()=>void}){
  const [data,setData]=useState<State|null>(null),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [draft,setDraft]=useState<Draft|null>(null),[saving,setSaving]=useState(false);
  const [history,setHistory]=useState<Passage[]|null>(null),[audio,setAudio]=useState<{url:string;key:string}|null>(null);
  const [draftLoaded,setDraftLoaded]=useState(false);
  const generation=useRef(0);
  const base='/api/lectures/'+lecture,draftKey='notetaker:transcript-draft:'+owner+':'+lecture;
  const refresh=useCallback(async()=>{
    const token=++generation.current;
    const result=await api<State>(base+'/transcript');
    if(token===generation.current)setData(result);
  },[base]);
  useEffect(()=>{
    let active=true;
    const load=async()=>{try{if(active)await refresh();}catch(err){if(active){if(err instanceof TranscriptError&&err.status===401)onSessionExpired();else setError(err instanceof Error?err.message:'The connection is unavailable.');}}};
    void load();const interval=setInterval(()=>void load(),4000);
    return()=>{active=false;++generation.current;clearInterval(interval);};
  },[refresh,onSessionExpired]);
  useEffect(()=>{
    try{const stored=JSON.parse(sessionStorage.getItem(draftKey)??'null');if(stored&&['segment','base','text','key'].every(k=>typeof stored[k]==='string'))setDraft(stored);}
    catch{setError('Browser draft recovery is unavailable. Keep this page open while correcting a passage.');}
    setDraftLoaded(true);
  },[draftKey]);
  useEffect(()=>{
    if(!draftLoaded)return;
    try{if(draft)sessionStorage.setItem(draftKey,JSON.stringify(draft));else sessionStorage.removeItem(draftKey);}
    catch{setError('Your correction is only in this open page. Save it before leaving.');}
  },[draft,draftKey,draftLoaded]);
  useEffect(()=>{
    onBusy(!!draft||saving);
    const unload=(event:BeforeUnloadEvent)=>{if(draft){event.preventDefault();event.returnValue='';}};
    const navigate=(event:MouseEvent)=>{if(draft&&(event.target as Element).closest?.('a[href]:not([download])')){event.preventDefault();setMessage('Save or cancel this correction before leaving the lecture.');}};
    window.addEventListener('beforeunload',unload);document.addEventListener('click',navigate,true);
    return()=>{onBusy(false);window.removeEventListener('beforeunload',unload);document.removeEventListener('click',navigate,true);};
  },[draft,saving,onBusy]);
  async function retry(){
    setSaving(true);setError('');
    try{const result=await api<State>(base+'/transcription',{method:'POST',headers:{'X-CSRF-Token':csrf}});setData(result);setMessage(result.status==='not_started'?'Record and save audio first.':result.status==='processed'?'The available audio is already processed.':'Retry requested. Follow the processing status above.');}
    catch(err){setError(err instanceof Error?err.message:'Could not retry transcription.');}
    finally{setSaving(false);}
  }
  async function save(){
    if(!draft)return;setSaving(true);setError('');
    try{
      await api(base+'/transcript/segments/'+draft.segment+'/corrections',{method:'POST',headers:{'X-CSRF-Token':csrf,'Idempotency-Key':draft.key},
        body:JSON.stringify({expected_version:draft.base,text:draft.text})});
      setDraft(null);setMessage('Correction saved as a new revision. The original words remain in passage history.');await refresh();
    }catch(err){setError(err instanceof Error?err.message:'Your correction could not be saved.');await refresh().catch(()=>{});}
    finally{setSaving(false);}
  }
  async function showHistory(passage:Passage){
    try{setHistory(await api<Passage[]>(base+'/transcript/segments/'+passage.segment_id+'/versions'));}
    catch(err){setError(err instanceof Error?err.message:'Passage history is unavailable.');}
  }
  const current=data?.snapshot?.segments.find(p=>p.segment_id===draft?.segment);
  return <section className="transcript-panel" aria-labelledby="transcript-title">
    <div className="section-row"><h2 id="transcript-title">Lecture transcript</h2><span className="prepared-badge">On this device</span></div>
    <p className="muted">Follow the lecturer’s words, listen to their source, and correct recognition errors. Detailed study notes come next.</p>
    <div className="transcript-status"><p role="status">{data?statuses[data.status]??'Checking transcript':'Checking saved speech…'}{data&&data.counts.completed>0?' · '+data.counts.completed+' of '+Object.values(data.counts).reduce((a,b)=>a+b,0)+' audio sections processed':''}</p>
      <button className="secondary" disabled={saving||!!draft} onClick={()=>void retry()}>Retry transcription</button></div>
    {data?.errors.includes('model_unavailable')&&<p className="error">The local speech model is unavailable. Your audio is saved and will wait until the model is ready.</p>}
    {!!data?.errors.length&&!data.errors.includes('model_unavailable')&&<p className="error">Some speech could not be processed. Saved audio and earlier transcript passages remain available. You can retry.</p>}
    {data?.waiting_for_audio&&<p className="small muted">This build transcribes each recording segment after it is stopped and all declared audio is saved. Recover any pending audio above.</p>}
    {!!data?.snapshot?.issues.length&&<p className="gap-notice">This transcript includes uncertainty, an interruption, or unfinished processing. Missing audio is not reconstructed.</p>}
    {error&&<p role="alert" className="error">{error}</p>}{message&&<p role="status" className="small">{message}</p>}
    {!data?.snapshot?.segments.length&&<p className="transcript-empty">{data?.status==='processed'?'No recognized words were returned. Non-silent audio without recognized words remains uncertain; listen to the saved recording.':'Timestamped passages will appear here after local transcription.'}</p>}
    <ol className="transcript-passages">{data?.snapshot?.segments.map(p=><li key={p.segment_id}>
      <div className="passage-heading"><button className="text-button" aria-label={'Play recording '+p.segment_number+' from '+stamp(p.start_sample,p.sample_rate)+' to '+stamp(p.end_sample,p.sample_rate)} onClick={()=>setAudio({url:p.audio_url,key:crypto.randomUUID()})}>▶ Segment {p.segment_number} · {stamp(p.start_sample,p.sample_rate)}–{stamp(p.end_sample,p.sample_rate)}</button><span className="small muted">{p.author==='student'?'Corrected by you':'Machine transcript'} · Revision {p.revision}</span></div>
      <p className="passage-text">{p.text}</p>
      {p.author==='machine'&&p.confidence.value!==null&&p.confidence.value<0.6&&<p className="gap-notice">Uncertain recognition — check the audio.</p>}
      <div className="passage-actions"><button className="text-button" disabled={!!draft||saving} onClick={()=>{setDraft({segment:p.segment_id,base:p.id,text:p.text,key:crypto.randomUUID()});setMessage('');setError('');}}>Correct passage</button><button className="text-button" onClick={()=>void showHistory(p)}>View history</button></div>
    </li>)}</ol>
    {draft&&<div className="transcript-editor"><label htmlFor="transcript-correction">Correct the lecturer’s words</label><p className="small muted">Keep your study explanations separate. This changes the transcript and preserves its original source.</p>
      <textarea id="transcript-correction" autoFocus maxLength={12000} value={draft.text} disabled={saving} onChange={event=>setDraft({...draft,text:event.target.value,key:crypto.randomUUID()})}/>
      {current&&current.id!==draft.base&&<div className="recovery-box"><p>This passage has a newer saved revision:</p><p>{current.text}</p><button className="secondary" disabled={saving} onClick={()=>setDraft({...draft,base:current.id,key:crypto.randomUUID()})}>Use latest revision as comparison base</button><p className="small">Your draft above is retained. Review both before saving.</p></div>}
      <div className="form-actions"><button className="secondary" disabled={saving} onClick={()=>{setDraft(null);setMessage('Correction cancelled. Saved transcript unchanged.');}}>Cancel correction</button><button className="primary" disabled={saving||!draft.text.trim()||!!current&&current.id!==draft.base} onClick={()=>void save()}>{saving?'Saving…':'Save correction'}</button></div>
    </div>}
    {audio&&<audio key={audio.key} className="audio-player" src={audio.url} controls autoPlay onError={()=>setError('This source audio is unavailable. Your transcript is retained.')}/>}
    {history&&<div className="transcript-history" role="region" aria-label="Passage revision history"><div className="section-row"><h3>Passage history</h3><button className="text-button" onClick={()=>setHistory(null)}>Close history</button></div>{history.map(p=><div key={p.id}><p className="small muted">Revision {p.revision} · {p.author==='student'?'Your correction':'Original recognition'}</p><p className="passage-text">{p.text}</p><button className="text-button" onClick={()=>setAudio({url:p.audio_url,key:crypto.randomUUID()})}>Listen to this source</button></div>)}</div>}
  </section>;
}

