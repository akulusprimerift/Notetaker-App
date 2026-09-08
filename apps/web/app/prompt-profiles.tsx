'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
type Prompts={detail_prompt:string;layout_prompt:string;instructions:string};
type Saved=Prompts&{id:string;name:string;version:number};
export default function PromptProfiles({prompts,onLoad,csrf}:{prompts:Prompts;onLoad:(value:Prompts)=>void;csrf:string}){
  const [rows,setRows]=useState<Saved[]>([]),[selected,setSelected]=useState(''),[name,setName]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
  const command=useRef<{body:string;path:string;key:string}|null>(null);
  const refresh=useCallback(async()=>{const response=await fetch('/api/prompt-profiles',{cache:'no-store'});if(!response.ok)throw new Error('Could not load saved profiles.');setRows(await response.json())},[]);
  useEffect(()=>{void refresh().catch(e=>setError(e.message))},[refresh]);
  async function save(update:boolean){
    const row=rows.find(r=>r.id===selected);if(update&&!row)return;
    const body=JSON.stringify({...prompts,name,expected_version:update?row!.version:0}),path='/api/prompt-profiles'+(update?'/'+row!.id:'');
    if(command.current?.body!==body||command.current.path!==path)command.current={body,path,key:crypto.randomUUID()};
    setBusy(true);setError('');setNotice('');
    try{const response=await fetch(path,{method:update?'PUT':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':command.current.key},body});const data=await response.json();if(!response.ok)throw new Error(data.error?.message??'Could not save the profile.');command.current=null;await refresh();setSelected(data.id);setNotice('Profile saved. You can use it in any lecture.');}
    catch(e){setError(e instanceof Error?e.message:'Could not save the profile.');await refresh().catch(()=>{})}finally{setBusy(false)}
  }
  return <section aria-label="Saved prompt profiles"><h3>Prompt profiles</h3><p className="small muted">Save your detail, layout and writing prompts to reuse across lectures.</p>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
    <label htmlFor="prompt-profile">Saved profile</label><select id="prompt-profile" value={selected} disabled={busy} onChange={e=>{setSelected(e.target.value);setName(rows.find(r=>r.id===e.target.value)?.name??'')}}><option value="">Choose a profile</option>{rows.map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</select>
    <button className="secondary full" disabled={busy||!selected} onClick={()=>{const row=rows.find(r=>r.id===selected);if(row){onLoad({detail_prompt:row.detail_prompt,layout_prompt:row.layout_prompt,instructions:row.instructions});setNotice('Prompts loaded below. Apply note preferences when ready.')}}}>Load profile prompts</button>
    <label htmlFor="profile-name">Profile name</label><input id="profile-name" value={name} maxLength={120} onChange={e=>setName(e.target.value)} placeholder="e.g. Detailed science notes"/>
    <button className="secondary full" disabled={busy||!name.trim()} onClick={()=>void save(false)}>Save prompts as new profile</button>
    {selected&&<button className="text-button" disabled={busy||!name.trim()} onClick={()=>void save(true)}>Update selected profile</button>}
  </section>;
}
