'use client';

import {useCallback, useEffect, useRef, useState} from 'react';

type Citation={source_id:string;quote:string;occurrence:number};
type Passage={id:string;evidence_kind:string;text:string;sources:Citation[]};
type Block={id:string;topic:string;kind:string;passages:Passage[]};
type Preference={version:number;model:string;digest:string;enabled:boolean};
type Revision={id:string;revision:number;created_at:string;content:{blocks:Block[];issues:{code:string;detail:string;source_ids:string[]}[];coverage:{source_id:string;disposition:string;reason:string}[]};metadata:{model:string};source_issues:unknown[]};
type State={status:string;preference:Preference|null;stale:boolean;error_code:string|null;revision:Revision|null};
type Model={name:string;digest:string;size:number};
type Source={id:string;text:string;audio_url:string;segment_number:number;start_sample:number;sample_rate:number};
const labels:Record<string,string>={choose_model:'Choose who takes your notes.',waiting_for_transcript:'Waiting for a saved transcript.',queued:'Your notes are queued.',generating:'Your model is writing study notes…',ready:'Your study notes are saved.',needs_attention:'Your notes need another attempt.',paused:'Automatic notes are paused.'};
const errors:Record<string,string>={model_unavailable:'Open Ollama and check that your selected model is installed.',model_changed:'The installed model changed. Select it again to use its new version.',invalid_output:'The model returned notes that failed the source or format checks. Try again; your last saved notes are still here.',truncated_output:'The model stopped before finishing the notes. Your last saved notes are still here.',context_limit:'This transcript exceeds the current note-generation capacity. It has been kept in full. Support for longer lectures is still being built.',worker_error:'The local note service could not finish. Try again.',model_context_unsupported:'This model does not support the required input capacity.'};

export default function Notes({lecture,csrf,onSessionExpired}:{lecture:string;csrf:string;onSessionExpired:()=>void}){
  const [state,setState]=useState<State|null>(null),[models,setModels]=useState<Model[]>([]),[selected,setSelected]=useState('');
  const [available,setAvailable]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [source,setSource]=useState<Source|null>(null),[quote,setQuote]=useState(''),[audio,setAudio]=useState(0);
  const alive=useRef(true),sourceRequest=useRef(0),sequence=useRef(0),command=useRef<{body:string;key:string}|null>(null);
  const sourcePanel=useRef<HTMLElement|null>(null);
  useEffect(()=>{if(source)sourcePanel.current?.focus()},[source]);
  const request=useCallback(async <T,>(path:string,init:RequestInit={}):Promise<T>=>{
    const response=await fetch('/api'+path,{...init,cache:'no-store',headers:{'Content-Type':'application/json',...init.headers}});
    if(response.status===401){onSessionExpired();throw new Error('The workspace is locked.')}
    if(!response.ok){const body=await response.json().catch(()=>null);throw new Error(body?.error?.message??'The workspace could not be reached. Try again.')}
    return response.json();
  },[onSessionExpired]);
  const path=`/lectures/${encodeURIComponent(lecture)}/notes`;
  const refresh=useCallback(async()=>{
    const ticket=++sequence.current;
    const data=await request<State>(path);
    if(alive.current&&ticket===sequence.current)setState(data);
  },[path,request]);
  const refreshModels=useCallback(async()=>{
    const data=await request<{models:Model[];available:boolean}>('/note-models');
    if(alive.current){setModels(data.models);setAvailable(data.available)}
  },[request]);
  useEffect(()=>{
    alive.current=true;
    const report=(err:unknown)=>{if(alive.current)setError(err instanceof Error?err.message:'Could not load notes.')};
    void refresh().catch(report);void refreshModels().catch(report);
    const timer=setInterval(()=>void refresh().catch(report),4000);
    return()=>{alive.current=false;sourceRequest.current++;sequence.current++;clearInterval(timer)};
  },[refresh,refreshModels]);
  async function choose(enabled=true){
    if(!state)return;
    const model=enabled?(selected||state.preference?.model):state.preference?.model;
    if(!model)return;
    const body=JSON.stringify({expected_version:state.preference?.version??0,model,enabled});
    if(command.current?.body!==body)command.current={body,key:crypto.randomUUID()};
    setBusy(true);setError('');
    try{await request(path+'/model',{method:'POST',body,headers:{'X-CSRF-Token':csrf,'Idempotency-Key':command.current.key}});command.current=null;setSelected('');await refresh()}
    catch(err){setError(err instanceof Error?err.message:'Could not save the model choice.');await refresh().catch(()=>{})}
    finally{if(alive.current)setBusy(false)}
  }
  async function retry(){
    setBusy(true);setError('');
    try{await request(path+'/retry',{method:'POST',body:'{}',headers:{'X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()}});await refresh()}
    catch(err){setError(err instanceof Error?err.message:'Could not retry notes.')}
    finally{if(alive.current)setBusy(false)}
  }
  async function openSource(citation:Citation){
    const ticket=++sourceRequest.current;setError('');setSource(null);
    try{const data=await request<Source>(`/lectures/${lecture}/sources/${citation.source_id}`);if(alive.current&&ticket===sourceRequest.current){setSource(data);setQuote(citation.quote);setAudio(0)}}
    catch(err){if(alive.current&&ticket===sourceRequest.current)setError(err instanceof Error?err.message:'Source unavailable.')}
  }
  const revision=state?.revision;
  return <div className="note-layout generated-notes"><section className="note-paper" aria-labelledby="notes-title">
    <div className="paper-heading"><h2 id="notes-title">Your lecture notes</h2><span>DETAILED · TOPIC OUTLINE</span></div>
    <div className="note-status"><p role="status">{state?labels[state.status]:'Opening your notes…'}</p>
      <p className="small muted">Your selected model turns the transcript into explanations, definitions and worked steps. You can check the evidence below.</p>
      {state?.status==='generating'&&<p className="small muted">Local generation can take several minutes. You can leave this page while it finishes.</p>}
      {error&&<p role="alert" className="error">{error}</p>}
      {state?.error_code&&<p className="error">{errors[state.error_code]??'The local note service needs attention.'}</p>}
      {state?.stale&&<p className="inline-notice">These saved notes use an earlier transcript or model choice. When automatic notes are enabled, a new result must pass checks before replacing them.</p>}
      {state&&(state.status==='needs_attention'||state.error_code)&&<button className="secondary" disabled={busy} onClick={()=>void retry()}>Retry notes</button>}
    </div>
    {revision?<div className="generated-content"><div className="note-revision"><span>Revision {revision.revision} · {revision.metadata.model}</span><a className="text-button" href={`/api${path}/revisions/${revision.id}/export`}>Export Markdown</a></div>
      <p className="small muted">AI-generated notes. Source links verify where the evidence came from; review important claims for accuracy.</p>
      {revision.content.blocks.map(block=><section className="study-block" key={block.id}><p className="eyebrow">{block.kind}</p><h3>{block.topic}</h3>{block.passages.map(passage=><div className="study-passage" key={passage.id}>
        <span className="evidence-label">{passage.evidence_kind==='lecture_paraphrase'?'From the lecture':passage.evidence_kind==='exact_quote'?'Exact lecture quote':passage.evidence_kind==='ai_explanation'?'Additional AI explanation':'Uncertain'}</span>
        {block.kind==='code'||block.kind==='equation'?<pre><code>{passage.text}</code></pre>:<p className="study-text">{passage.text}</p>}
        <div className="citation-list">{passage.sources.map((citation,index)=><button key={index} className="text-button" onClick={()=>void openSource(citation)}>Source {index+1} ↗<span className="sr-only"> for {block.topic}, passage {passage.id}</span></button>)}</div>
      </div>)}</section>)}
      {(revision.content.issues.length>0||revision.source_issues.length>0||revision.content.coverage.some(c=>c.disposition!=='used'))&&<section className="note-review"><h3>Worth reviewing</h3>
        {revision.source_issues.length>0&&<p>The transcript includes recording gaps or uncertain recognition. Check the warnings in the transcript below.</p>}
        {revision.content.issues.map((issue,index)=><p key={index}>{issue.detail}</p>)}
        {revision.content.coverage.filter(c=>c.disposition!=='used').map(item=><p key={item.source_id}>{item.disposition==='unclear'?'Unclear passage':'Omitted passage'}: {item.reason} <button className="text-button" onClick={()=>void openSource({source_id:item.source_id,quote:'',occurrence:0})}>Review source</button></p>)}
      </section>}
    </div>:<div className="note-placeholder"><span className="paper-icon" aria-hidden="true">≡</span><h3>Listen to the lecture. Let your model take notes.</h3><p>{state?.preference?`Your selected model is ${state.preference.model}. Your notes will appear here when they are ready.`:'Choose a local model once for this lecture. Notes will be created when the saved transcript is ready, and refreshed after corrections.'}</p></div>}
  </section><aside className="lecture-details note-controls"><h2>Your note-taking model</h2><p className="small muted">Runs on this Windows machine through Ollama. Detailed notes; additional AI explanations are off.</p>
    <label htmlFor="note-model">Local model</label><select id="note-model" value={selected||state?.preference?.model||''} disabled={busy} onChange={event=>setSelected(event.target.value)}><option value="">Choose a model</option>{models.map(model=><option key={model.name} value={model.name}>{model.name}</option>)}{state?.preference&&!models.some(m=>m.name===state.preference?.model)&&<option value={state.preference.model}>{state.preference.model} (unavailable)</option>}</select>
    {(!available||!models.length)&&<p className="small">Open Ollama to use an installed Qwen model. More model families and cloud connections are planned.</p>}
    <button className="primary full" disabled={busy||!state||!(selected||state.preference?.model)||(!selected&&!!state.preference?.enabled)} onClick={()=>void choose()}>{busy?'Saving…':state?.preference?'Use this model':'Start automatic notes'}</button>
    {state?.preference?.enabled&&<button className="text-button" disabled={busy} onClick={()=>void choose(false)}>Pause automatic notes</button>}
    <button className="text-button" disabled={busy} onClick={()=>void refreshModels().catch(err=>setError(err instanceof Error?err.message:'Could not refresh models.'))}>Refresh model list</button>
    <p className="small muted">Automatic notes continue when this page is closed, while the app services are running.</p>
    {source&&<section ref={sourcePanel} tabIndex={-1} className="note-source" aria-label="Note source"><div className="section-row"><h3>Lecture evidence</h3><button className="text-button" onClick={()=>{sourceRequest.current++;setSource(null)}}>Close source</button></div><p className="small">Recording {source.segment_number} · {(source.start_sample/source.sample_rate).toFixed(1)} seconds</p>{quote&&<blockquote>{quote}</blockquote>}<p className="study-text">{source.text}</p><button className="secondary" onClick={()=>setAudio(value=>value+1)}>Play source audio</button>{audio>0&&<audio key={`${source.id}-${audio}`} controls autoPlay src={source.audio_url} onError={()=>setError('The saved source audio is unavailable. The transcript is still shown.')}/>}</section>}
  </aside></div>;
}
