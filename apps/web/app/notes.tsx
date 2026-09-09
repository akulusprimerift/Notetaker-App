'use client';
import PromptProfiles from './prompt-profiles';
import ReviewNotice from './review-notice';

import {useCallback, useEffect, useRef, useState} from 'react';
import NoteEditor,{type Editing} from './note-editor';

type Citation={source_id:string;quote:string;occurrence:number};
type Passage={id:string;evidence_kind:string;text:string;sources:Citation[];student_edited?:boolean};
type Block={id:string;topic:string;kind:string;passages:Passage[]};
type Preference={version:number;model:string;digest:string;enabled:boolean};
export type Revision={student?:boolean;profile:Profile;id:string;revision:number;created_at:string;content:{blocks:Block[];issues:{code:string;detail:string;source_ids:string[]}[];coverage:{source_id:string;disposition:string;reason:string}[]};metadata:{model:string};source_issues:unknown[]};
type Profile={depth:string;format:string;instructions:string;detail_prompt:string;layout_prompt:string};
type State={editing:Editing;processing:{newer_transcript_pending:boolean;request_age_seconds:number};profile:Profile;status:string;preference:Preference|null;stale:boolean;error_code:string|null;revision:Revision|null};
type Model={name:string;digest:string;size:number};
type Source={source_kind?:string;label?:string;id:string;text:string;audio_url:string;segment_number:number;start_sample:number;sample_rate:number};
const labels:Record<string,string>={choose_model:'Choose who takes your notes.',waiting_for_transcript:'Waiting for transcript passages.',queued:'Your notes are queued.',generating:'Your model is writing study notes…',ready:'Your study notes are saved.',needs_attention:'Your notes need another attempt.',paused:'Automatic notes are paused.'};
const errors:Record<string,string>={model_unavailable:'Open Ollama and check that your selected model is installed.',model_changed:'The installed model changed. Select it again to use its new version.',invalid_output:'The model returned notes that failed the source or format checks. Try again; any previously saved notes are preserved.',truncated_output:'The model stopped before finishing the notes. Your last saved notes are still here.',context_limit:'This transcript exceeds the current note-generation capacity. It has been kept in full. Support for longer lectures is still being built.',worker_error:'The local note service could not finish. Try again.',model_context_unsupported:'This model does not support the required input capacity.'};

export default function Notes({lecture,csrf,onSessionExpired}:{lecture:string;csrf:string;onSessionExpired:()=>void}){
  const [state,setState]=useState<State|null>(null),[models,setModels]=useState<Model[]>([]),[selected,setSelected]=useState('');
  const [connectionError,setConnectionError]=useState('');
  const [reading,setReading]=useState<Revision|null>(null);
  const applyState=useCallback((data:State)=>{setState(data);setConnectionError('');},[]);
  useEffect(()=>{if(!reading&&(state?.editing.selected||state?.revision))setReading(state.editing.selected??state.revision);},[reading,state]);
  const [preview,setPreview]=useState<{text:string;active:boolean}>({text:'',active:false});
  const previewPanel=useRef<HTMLDivElement|null>(null),followPreview=useRef(true);
  useEffect(()=>{if(previewPanel.current&&followPreview.current)previewPanel.current.scrollTop=previewPanel.current.scrollHeight},[preview.text]);
  const [custom,setCustom]=useState<Profile|null>(null);
  const profile=custom??state?.profile??{depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''};
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
  useEffect(()=>{
    const events=new EventSource('/api'+path+'/stream');
    events.onmessage=event=>{try{setPreview(JSON.parse(event.data))}catch{setPreview({text:'',active:false})}};
    events.addEventListener('removed',()=>{events.close();setPreview({text:'',active:false});window.dispatchEvent(new Event('deletion-started'))});
    events.addEventListener('expired',()=>{events.close();onSessionExpired()});
    events.onerror=()=>{setPreview(current=>({...current,active:false}))};
    return()=>events.close();
  },[path,onSessionExpired]);
  const refresh=useCallback(async()=>{
    const ticket=++sequence.current;
    const data=await request<State>(path);
    if(alive.current&&ticket===sequence.current)applyState(data);
  },[path,request,applyState]);
  const refreshModels=useCallback(async()=>{
    const data=await request<{models:Model[];available:boolean}>('/note-models');
    if(alive.current){setModels(data.models);setAvailable(data.available)}
  },[request]);
  useEffect(()=>{
    alive.current=true;
    const report=(err:unknown)=>{if(alive.current)setConnectionError(err instanceof Error?err.message:'Could not load notes.')};
    const live=(event:Event)=>{const detail=(event as CustomEvent).detail;if(detail.lecture===lecture){sequence.current++;applyState(detail.snapshot.notes);}};
    window.addEventListener('lecture-snapshot',live);
    void refresh().catch(report);void refreshModels().catch(report);
    const timer=setInterval(()=>void refresh().catch(report),4000);
    return()=>{alive.current=false;sourceRequest.current++;sequence.current++;clearInterval(timer);window.removeEventListener('lecture-snapshot',live)};
  },[refresh,refreshModels,lecture,applyState]);
  async function choose(enabled=true){
    if(!state)return;
    const model=enabled?(selected||state.preference?.model):state.preference?.model;
    if(!model)return;
    const body=JSON.stringify({expected_version:state.preference?.version??0,model,enabled,...(enabled?{...profile,depth:'detailed',format:'topic_outline'}:{})});
    if(command.current?.body!==body)command.current={body,key:crypto.randomUUID()};
    setBusy(true);setError('');
    try{await request(path+'/model',{method:'POST',body,headers:{'X-CSRF-Token':csrf,'Idempotency-Key':command.current.key}});command.current=null;setSelected('');if(enabled)setCustom(null);await refresh()}
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
  const selectedRevision=state?.editing.selected??state?.revision;
  const revision=reading??selectedRevision;
  const pending=reading&&selectedRevision&&reading.id!==selectedRevision.id?selectedRevision:null;
  const savedProfile=revision?.profile??state?.profile;
  return <div className="note-layout generated-notes"><section className="note-paper" aria-labelledby="notes-title">
    <div className="paper-heading"><h2 id="notes-title">Your lecture notes</h2><span>{savedProfile?.detail_prompt?.trim()?'CUSTOM DETAIL':(savedProfile?.depth??'detailed').toUpperCase()} · {savedProfile?.layout_prompt?.trim()?'CUSTOM LAYOUT':(savedProfile?.format??'topic_outline').replaceAll('_',' ').toUpperCase()}</span></div>
    <div className="note-status"><p role="status">{state?labels[state.status]:'Opening your notes…'}</p>
      <p className="small muted">Your selected model turns the transcript into explanations, definitions and worked steps. You can check the evidence below.</p>
      {state?.processing?.newer_transcript_pending&&<p className="small muted">New transcript passages are waiting for the next note update.</p>}
      {state?.status==='generating'&&<p className="small muted">Your model is writing from accumulated transcript passages. New speech continues to be transcribed.</p>}
      {connectionError&&<p role="status" className="error">{connectionError}</p>}
      {error&&<p role="alert" className="error">{error}</p>}
      {state?.error_code&&<p className="error">{errors[state.error_code]??'The local note service needs attention.'}</p>}
      {state?.stale&&<p className="inline-notice">These saved notes use an earlier transcript or model choice. When automatic notes are enabled, a new result must pass checks before replacing them.</p>}
      {state&&(state.status==='needs_attention'||state.error_code)&&<button className="secondary" disabled={busy} onClick={()=>void retry()}>Retry notes</button>}
    </div>
    {(preview.active||preview.text)&&<section className="streaming-notes" aria-label="Notes being written"><h3>{preview.active?'Writing now…':'Reconnecting to the writing preview…'}</h3><p className="small muted">Live draft · source checks run before these notes are saved. Scroll up to pause following the newest text.</p><div ref={previewPanel} tabIndex={0} className="streaming-text" onScroll={event=>{const panel=event.currentTarget;followPreview.current=panel.scrollHeight-panel.scrollTop-panel.clientHeight<30}}>{preview.text||'Preparing the next note passages…'}</div></section>}
    {pending&&<div className="inline-notice"><p>New notes are ready. Your current reading copy stays in place until you open them.</p><button className="secondary" onClick={()=>{setReading(pending);}}>Show updated notes (revision {pending.revision})</button></div>}
    {revision?<div className="generated-content"><div className="note-revision"><span>{revision.student?'Student revision':'Revision'} {revision.revision} · {revision.metadata.model}</span><a className="text-button" href={`/api${path}/${revision.student?'edits':'revisions'}/${revision.id}/export`}>Export Markdown</a></div>
      <p className="small muted">{revision.student?'Your selected student revision. Student changes retain original source links for review.':'AI-generated notes. Source links verify where the evidence came from; review important claims for accuracy.'}</p>
      {state&&<NoteEditor lecture={lecture} revision={revision} editing={state.editing} csrf={csrf} onExpired={onSessionExpired} onSaved={saved=>{setReading(saved);void refresh().catch(()=>{})}}/>}
      {revision.content.blocks.map(block=><section className={`study-block ${revision.profile?.format==='cornell'&&!revision.profile.layout_prompt?'cornell-block':''}`} key={block.id}><div className="study-block-title"><p className="eyebrow">{block.kind}</p><h3>{block.topic}</h3></div>{block.passages.map(passage=><div className="study-passage" key={passage.id}>
        <span className="evidence-label">{passage.student_edited?'Student revision · review against the original sources':passage.evidence_kind==='material_paraphrase'?'From uploaded material and cited evidence':passage.evidence_kind==='lecture_paraphrase'?'From the lecture':passage.evidence_kind==='exact_quote'?'Exact lecture quote':passage.evidence_kind==='ai_explanation'?'Additional AI explanation':'Uncertain'}</span>
        {block.kind==='code'||block.kind==='equation'?<pre><code>{passage.text}</code></pre>:<p className="study-text">{passage.text}</p>}
        <div className="citation-list">{passage.sources.map((citation,index)=><button key={index} className="text-button" onClick={()=>void openSource(citation)}>Source {index+1} ↗<span className="sr-only"> for {block.topic}, passage {passage.id}</span></button>)}</div>
      </div>)}</section>)}
      {(revision.content.issues.length>0||revision.source_issues.length>0||revision.content.coverage.some(c=>c.disposition!=='used'))&&<ReviewNotice key={revision.id} lecture={lecture} revision={revision.id}>
        {revision.source_issues.length>0&&<p>The transcript includes recording gaps or uncertain recognition. Check the warnings in the transcript below.</p>}
        {revision.content.issues.map((issue,index)=><p key={index}>{issue.detail}</p>)}
        {revision.content.coverage.filter(c=>c.disposition!=='used').map(item=><p key={item.source_id}>{item.disposition==='unclear'?'Unclear passage':'Omitted passage'}: {item.reason} <button className="text-button" onClick={()=>void openSource({source_id:item.source_id,quote:'',occurrence:0})}>Review source</button></p>)}
      </ReviewNotice>}
    </div>:<div className="note-placeholder"><span className="paper-icon" aria-hidden="true">≡</span><h3>Listen to the lecture. Let your model take notes.</h3><p>{state?.preference?`Your selected model is ${state.preference.model}. Your notes will appear here when they are ready.`:'Choose a local model once for this lecture. Notes will be created when the saved transcript is ready, and refreshed after corrections.'}</p></div>}
  </section><aside className="lecture-details note-controls"><h2>Your note-taking model</h2><p className="small muted">Works with any course. Your model derives the subject from the transcript and runs locally through Ollama.</p>
    <label htmlFor="note-model">Local model</label><select id="note-model" value={selected||state?.preference?.model||''} disabled={busy} onChange={event=>setSelected(event.target.value)}><option value="">Choose a model</option>{models.map(model=><option key={model.name} value={model.name}>{model.name}</option>)}{state?.preference&&!models.some(m=>m.name===state.preference?.model)&&<option value={state.preference.model}>{state.preference.model} (unavailable)</option>}</select>
    {(!available||!models.length)&&<p className="small">Open Ollama to use an installed Qwen model. More model families and cloud connections are planned.</p>}
    <PromptProfiles csrf={csrf} prompts={profile} onLoad={value=>setCustom({...profile,...value})}/>
    <label htmlFor="note-detail-prompt">Describe your detail level (optional)</label><textarea id="note-detail-prompt" value={profile.detail_prompt} maxLength={2000} rows={4} disabled={busy} onChange={e=>setCustom({...profile,detail_prompt:e.target.value})} placeholder="e.g. Assume I am new to the subject. Explain each concept fully, keep every worked example, and include a short recap."/>
    <label htmlFor="note-layout-prompt">Describe your layout (optional)</label><textarea id="note-layout-prompt" value={profile.layout_prompt} maxLength={2000} rows={4} disabled={busy} onChange={e=>setCustom({...profile,layout_prompt:e.target.value})} placeholder="e.g. Group by concept, with a definition, explanation, example and self-check question under each heading."/><p className="small muted">Tell your model how much detail you want and how to organize it. Leave these blank for detailed notes grouped by topic. Source links are retained.</p>
    <label htmlFor="note-instructions">Writing preferences (optional)</label><textarea id="note-instructions" value={profile.instructions} maxLength={1000} rows={3} disabled={busy} onChange={e=>setCustom({...profile,instructions:e.target.value})} placeholder="e.g. Explain terminology in plain language and emphasize cause and effect."/>
    <button className="primary full" disabled={busy||!state||!(selected||state.preference?.model)||(!selected&&!custom&&!!state.preference?.enabled)} onClick={()=>void choose()}>{busy?'Saving…':state?.preference?'Apply note preferences':'Start automatic notes'}</button>
    {state?.revision&&<button className="secondary full" disabled={busy||!state.preference?.enabled} onClick={()=>void choose()}>Regenerate notes</button>}
    {state?.preference?.enabled&&<button className="text-button" disabled={busy} onClick={()=>void choose(false)}>Pause automatic notes</button>}
    <button className="text-button" disabled={busy} onClick={()=>void refreshModels().catch(err=>setError(err instanceof Error?err.message:'Could not refresh models.'))}>Refresh model list</button>
    <p className="small muted">Automatic notes continue when this page is closed, while the app services are running.</p>
    {source&&<section ref={sourcePanel} tabIndex={-1} className="note-source" aria-label="Note source"><div className="section-row"><h3>{source.source_kind?'Uploaded evidence':'Lecture evidence'}</h3><button className="text-button" onClick={()=>{sourceRequest.current++;setSource(null)}}>Close source</button></div><p className="small">{source.source_kind?source.label:<>Recording {source.segment_number} · {(source.start_sample/source.sample_rate).toFixed(1)} seconds</>}</p>{quote&&<blockquote>{quote}</blockquote>}<p className="study-text">{source.text}</p>{!source.source_kind&&<button className="secondary" onClick={()=>setAudio(value=>value+1)}>Play source audio</button>}{audio>0&&<audio key={`${source.id}-${audio}`} controls autoPlay src={source.audio_url} onError={()=>setError('The saved source audio is unavailable. The transcript is still shown.')}/>}</section>}
  </aside></div>;
}
