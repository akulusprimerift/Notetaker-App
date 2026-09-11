'use client';

import {FormEvent, useCallback, useEffect, useState} from 'react';

type Connection={name:string;digest:string;provider?:string};
type Props={csrf:string;onChanged:()=>void;onSessionExpired:()=>void};
const labels:Record<string,string>={openai:'OpenAI API',anthropic:'Claude API',chatgpt:'ChatGPT subscription · Codex', 'claude-subscription':'Claude subscription · Claude Code'};
const subscriptions=new Set(['chatgpt','claude-subscription']);

export default function ProviderConnections({csrf,onChanged,onSessionExpired}:Props){
  const [provider,setProvider]=useState('openai'),[model,setModel]=useState(''),[apiKey,setApiKey]=useState(''),[executable,setExecutable]=useState('');
  const [rows,setRows]=useState<Connection[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const subscription=subscriptions.has(provider);
  async function request<T>(path:string,init:RequestInit={}):Promise<T>{
    const response=await fetch('/api'+path,{...init,cache:'no-store',headers:{'Content-Type':'application/json',...init.headers}});
    if(response.status===401){onSessionExpired();throw new Error('The workspace is locked.');}
    const result=await response.json().catch(()=>null);
    if(!response.ok)throw new Error(result?.error?.message??'The provider connection could not be reached.');
    return result as T;
  }
  const load=useCallback(async()=>{try{const result=await request<{connections:Connection[]}>('/provider-connections');setRows(result.connections);}catch(err){setError(err instanceof Error?err.message:'Could not load provider connections.');}},[csrf,onSessionExpired]);
  useEffect(()=>{void load();},[load]);
  function resetForm(){setModel('');setApiKey('');setExecutable('');}
  async function save(event:FormEvent){
    event.preventDefault();if(!model.trim()||(!subscription&&!apiKey.trim())||(subscription&&!executable)){setError(subscription?'Choose a model and the official provider client.':'Enter a model ID and API key.');return;}
    setBusy(true);setError('');setNotice('');
    try{
      const result=await request<{connections:Connection[]}>('/provider-connections',{method:'POST',headers:{'X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({provider,model:model.trim(),api_key:apiKey,executable})});
      setRows(result.connections);
      if(subscription){
        await request(`/provider-connections/${provider}/sign-in`,{method:'POST',headers:{'X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},body:'{}'});
        setNotice('Signed in through the official provider client. Choose this connection in the note model list.');
      }else setNotice('Connection saved. Choose it in the note model list for a lecture.');
      resetForm();onChanged();
    }catch(err){setError(err instanceof Error?err.message:'Could not save the provider connection.');}finally{setBusy(false);}
  }
  async function chooseClient(){
    if(!window.desktopApp){setError('Official subscription clients can be linked from the Electron desktop app.');return;}
    try{setExecutable(await window.desktopApp.chooseProviderClient());setError('');}catch(err){setError(err instanceof Error?err.message:'Could not choose the provider client.');}
  }
  async function remove(row:Connection,signOut=false){
    const ident=row.provider??row.name.split('/')[0];setBusy(true);setError('');setNotice('');
    try{if(signOut)await request(`/provider-connections/${ident}/sign-out`,{method:'POST',headers:{'X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},body:'{}'});else await request(`/provider-connections/${ident}`,{method:'DELETE',headers:{'X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()}});await load();onChanged();setNotice(signOut?'Signed out and removed from Notetaker.':'Disconnected from Notetaker.');}
    catch(err){setError(err instanceof Error?err.message:'Could not update the provider connection.');}finally{setBusy(false);}
  }
  return <details className="provider-connections" open><summary>Connect another note provider</summary><div className="provider-connection-copy"><p>Use an API key or an installed official client. Notetaker never asks for your ChatGPT or Claude password and never reads another app’s sign-in tokens.</p><p className="small muted">Cloud note generation sends the selected transcript, selected material text and note prompts to the provider. Audio transcription stays local. You will confirm cloud processing when choosing it for a lecture.</p></div>
    <form className="provider-connection-form" onSubmit={save}><label htmlFor="provider-choice">Provider</label><select id="provider-choice" value={provider} disabled={busy} onChange={event=>{setProvider(event.target.value);setError('');setNotice('');resetForm();}}>{Object.entries(labels).map(([value,label])=><option value={value} key={value}>{label}</option>)}</select><label htmlFor="provider-model">Model ID</label><input id="provider-model" value={model} disabled={busy} onChange={event=>setModel(event.target.value)} placeholder={subscription?'e.g. sonnet or gpt-5':'e.g. gpt-5-mini or claude-sonnet-4-5'}/>{subscription?<><label htmlFor="provider-client">Official client</label><div className="provider-client-picker"><input id="provider-client" value={executable} readOnly disabled={busy} placeholder="Choose the installed .exe"/><button type="button" className="secondary" disabled={busy||typeof window==='undefined'||!window.desktopApp} onClick={()=>void chooseClient()}>Choose client</button></div><p className="small muted">The separate client profile is used for this app. Its sign-in opens in your system browser.</p></>:<><label htmlFor="provider-api-key">API key</label><input id="provider-api-key" type="password" autoComplete="off" value={apiKey} disabled={busy} onChange={event=>setApiKey(event.target.value)} placeholder="Stored with Windows protected storage"/><p className="small muted">API billing is separate from a ChatGPT or Claude consumer subscription.</p></>}<button className="primary" disabled={busy||!model.trim()||(subscription?!executable:!apiKey.trim())}>{busy?'Connecting…':subscription?'Save and sign in':'Save connection'}</button></form>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status" className="inline-notice">{notice}</p>}
    <div className="provider-connection-list"><p className="eyebrow">CONNECTED PROVIDERS</p>{rows.length===0?<p className="small muted">No providers connected yet.</p>:rows.map(row=>{const ident=row.provider??row.name.split('/')[0];return <div className="provider-connection-row" key={row.name}><div><strong>{labels[ident]??ident}</strong><span>{row.name.split('/').slice(1).join('/')}</span></div><div className="provider-connection-actions">{subscriptions.has(ident)&&<button type="button" className="text-button" disabled={busy} onClick={()=>void remove(row,true)}>Sign out</button>}<button type="button" className="text-button" disabled={busy} onClick={()=>void remove(row)}>Disconnect</button></div></div>})}</div>
  </details>;
}
