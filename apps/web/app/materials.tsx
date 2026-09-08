'use client';
import {useCallback,useEffect,useRef,useState} from 'react';

type Material={id:string;name:string;kind:string;pages:{label:string;text:string}[]};
export default function Materials({course,lecture,csrf}:{course:string;lecture?:string;csrf:string}){
  const path=lecture?`/lectures/${lecture}/materials`:`/courses/${course}/materials`;
  const [rows,setRows]=useState<Material[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const [kind,setKind]=useState('syllabus');
  const pending=useRef<{body:string;key:string}|null>(null);
  const load=useCallback(async()=>{const r=await fetch(`/api${path}`,{cache:'no-store'});if(!r.ok)throw new Error('Could not load course materials.');setRows(await r.json());},[path]);
  useEffect(()=>{void load().catch(e=>setError(e.message));},[load]);
  async function upload(file:File){
    setBusy(true);setError('');setNotice('');
    try{
      if(file.size>8*1024*1024)throw new Error('Choose a file up to 8 MiB.');
      const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('The file could not be read.'));reader.readAsDataURL(file);});
      const body=JSON.stringify({name:file.name,kind,data,expected_count:rows.length});
      if(pending.current?.body!==body)pending.current={body,key:crypto.randomUUID()};
      const response=await fetch(`/api${path}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':pending.current.key},body});
      if(!response.ok){const result=await response.json();if(response.status===409){pending.current=null;await load();}throw new Error(result.error?.message??'Upload failed. Try again.');}
      pending.current=null;await load();setNotice('Material saved. Automatic notes will be restructured using the transcript and uploaded text. Saved student edits and final snapshots are preserved.');
    }catch(e){setError(e instanceof Error?e.message:'Upload failed.');}finally{setBusy(false);}
  }
  return <section className="note-source" aria-label="Course materials"><h2>{lecture?'Lecture materials':'Syllabus and course materials'}</h2><p>{lecture?'Upload slides before or after recording.':'Course uploads apply to current and future lectures.'} New notes stream in the lecture workspace when a local model is enabled and a transcript is available.</p><p className="small muted">PPTX, DOCX, TXT or Markdown · 8 MiB maximum. Text only: images, diagrams, embedded objects and speaker notes are not interpreted. Review extracted text below. Original files are retained.</p>
    <label>Material type <select value={kind} disabled={busy} onChange={e=>setKind(e.target.value)}><option value="syllabus">Syllabus</option><option value="curriculum">Curriculum</option><option value="slides">Lecture slides</option></select></label>
    <label>Upload material <input type="file" accept=".pptx,.docx,.txt,.md" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void upload(file);e.target.value='';}}/></label>
    {busy&&<p role="status">Saving and reading your material…</p>}{error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {rows.map(row=><details key={row.id}><summary>{row.name} · {row.kind} · {row.pages.length} pages/slides</summary><a href={`/api/courses/${course}/materials/${row.id}/download`} download={row.name}>Download original</a>{row.pages.map((page,i)=><div key={i}><h3>{page.label}</h3><p className="study-text">{page.text||'No readable text. Visual content has not been interpreted.'}</p></div>)}</details>)}
  </section>;
}
