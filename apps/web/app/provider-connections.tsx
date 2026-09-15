'use client';

import {FormEvent, useCallback, useEffect, useState} from 'react';

type Connection={name:string;digest:string;provider?:string};
type Props={csrf:string;onChanged:()=>void;onSessionExpired:()=>void};
const labels:Record<string,string>={openai:'OpenAI API',anthropic:'Claude API',chatgpt:'ChatGPT', 'claude-subscription':'Claude subscription'};

export default function ProviderConnections({csrf,onChanged,onSessionExpired}:Props){
  const [provider,setProvider]=useState('openai'),[apiKey,setApiKey]=useState('');
  const [rows,setRows]=useState<Connection[]>([]),[busy,setBusy]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const request=useCallback(async <T,>(path:string,init:RequestInit={}):Promise<T>=>{
    const response=await fetch('/api'+path,{...init,cache:'no-store',headers:{'Content-Type':'application/json',...init.headers}});
    if(response.status===401){onSessionExpired();throw new Error('The workspace is locked.');}
    const result=await response.json().catch(()=>null);
    if(!response.ok)throw new Error(result?.error?.message??'The provider connection could not be reached.');
    return result as T;
  },[onSessionExpired]);
  const load=useCallback(async()=>{try{const result=await request<{connections:Connection[]}>('/provider-connections');setRows(result.connections);}catch(err){setError(err instanceof Error?err.message:'Could not load provider connections.');}},[request]);
  useEffect(()=>{void load();},[load]);
  const headers=()=>({'X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()});
  function changed(){onChanged();window.dispatchEvent(new Event('provider-connections-changed'));}
  async function save(event:FormEvent){
    event.preventDefault();if(!apiKey.trim())return;
    setBusy('api');setError('');setNotice('');
    try{
      const result=await request<{connections:Connection[]}>('/provider-connections',{method:'POST',headers:headers(),body:JSON.stringify({provider,api_key:apiKey})});
      setRows(result.connections);setApiKey('');changed();setNotice('API key connected. Available text models are ready in Note preferences.');
    }catch(err){setError(err instanceof Error?err.message:'Could not connect this API key.');}finally{setBusy('');}
  }
  async function signIn(){
    setBusy('chatgpt');setError('');setNotice('Opening your default browser. Finish signing in there, then return here.');
    try{
      const result=await request<{connections:Connection[]}>('/provider-connections/chatgpt/sign-in',{method:'POST',headers:headers(),body:'{}'});
      setRows(result.connections);changed();setNotice('ChatGPT linked. Choose an available model in your lecture’s Note preferences.');
    }catch(err){setNotice('');setError(err instanceof Error?err.message:'Could not link ChatGPT.');}finally{setBusy('');}
  }
  async function remove(ident:string){
    setBusy(ident);setError('');setNotice('');
    try{
      const subscription=ident==='chatgpt'||ident==='claude-subscription';
      const result=await request<{notice?:string}>(`/provider-connections/${ident}${subscription?'/sign-out':''}`,{method:subscription?'POST':'DELETE',headers:headers(),...(subscription?{body:'{}'}:{})});
      await load();changed();setNotice(result.notice||'Disconnected from Notetaker. Saved lecture notes are preserved.');
    }catch(err){setError(err instanceof Error?err.message:'Could not disconnect.');}finally{setBusy('');}
  }
  async function refresh(ident:string){
    setBusy(ident);setError('');setNotice('');
    try{const result=await request<{connections:Connection[]}>(`/provider-connections/${ident}/refresh`,{method:'POST',headers:headers(),body:'{}'});setRows(result.connections);changed();setNotice('Model list refreshed from your connected account.');}
    catch(err){setError(err instanceof Error?err.message:'Could not refresh models.');}finally{setBusy('');}
  }
  const providers=[...new Set(rows.map(row=>row.provider??row.name.split('/')[0]))];
  return <section className="account-settings" aria-label="Provider connections">
    <p className="muted">Connect once, then choose a model for each lecture. Your password stays with the provider.</p>
    <h3>Subscription accounts</h3>
    <div className="account-grid">
      <section className="account-card"><span className="account-mark" aria-hidden="true">G</span><h3>ChatGPT</h3><p>Link an eligible paid subscription in your browser. The sign-in helper is included with Notetaker.</p><p className="small muted">Shows models available through Codex. The ChatGPT website’s full model menu is not exposed to this app. Your plan’s limits apply.</p><button type="button" className="primary" disabled={Boolean(busy)||providers.includes('chatgpt')} onClick={()=>void signIn()}>{busy==='chatgpt'?'Waiting for sign-in…':providers.includes('chatgpt')?'ChatGPT linked':'Link ChatGPT'}</button></section>
      <section className="account-card"><span className="account-mark" aria-hidden="true">C</span><h3>Claude</h3><p>Subscription linking is not available for this app yet.</p><p className="small muted">Anthropic requires approval for third-party subscription sign-in. You can connect a Claude API key below; API usage is billed separately.</p><span className="account-status">Requires provider approval</span></section>
    </div>
    <form className="account-api" onSubmit={save}><h3>API keys</h3><p className="small muted">Paste your key to load available text models. API billing is separate from a ChatGPT or Claude subscription.</p><label htmlFor="provider-choice">API provider</label><select id="provider-choice" value={provider} disabled={Boolean(busy)} onChange={event=>{setProvider(event.target.value);setApiKey('');setError('');setNotice('');}}><option value="openai">OpenAI API</option><option value="anthropic">Claude API</option></select><label htmlFor="provider-api-key">API key</label><input id="provider-api-key" type="password" autoComplete="off" value={apiKey} disabled={Boolean(busy)} onChange={event=>setApiKey(event.target.value)} placeholder="Paste your API key"/><button className="primary" disabled={Boolean(busy)||!apiKey.trim()}>{busy==='api'?'Checking key and loading models…':'Connect API key'}</button></form>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status" className="inline-notice">{notice}</p>}
    <div className="provider-connection-list"><h3>Connected accounts</h3>{providers.length===0?<p className="small muted">No accounts connected yet.</p>:providers.map(ident=><div className="provider-connection-row" key={ident}><div><strong>{labels[ident]??ident}</strong><details><summary>{rows.filter(row=>(row.provider??row.name.split('/')[0])===ident).length} model choices</summary><ul>{rows.filter(row=>(row.provider??row.name.split('/')[0])===ident).map(row=><li key={row.name}>{row.name.split('/').slice(1).join('/')}</li>)}</ul></details></div><div className="provider-connection-actions">{ident!=='claude-subscription'&&<button type="button" className="text-button" disabled={Boolean(busy)} onClick={()=>void refresh(ident)}>Refresh models</button>}<button type="button" className="text-button" disabled={Boolean(busy)} onClick={()=>void remove(ident)}>Disconnect {labels[ident]??ident}</button></div></div>)}</div>
    <p className="small muted account-privacy">Keys use Windows protected storage. Cloud notes send selected transcript passages, material text and prompts to your chosen provider only after you enable cloud processing for that lecture. Audio transcription stays local.</p>
  </section>;
}
