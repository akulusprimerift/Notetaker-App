'use client';

import {FormEvent, useCallback, useEffect, useRef, useState} from 'react';

type Material={id:string;name:string;kind:string;pages:{label:string;text:string}[]};
const MAX_BYTES=8*1024*1024;
const kindLabels:Record<string,string>={syllabus:'Syllabus',curriculum:'Curriculum',slides:'Lecture slides'};
const size=(bytes:number)=>bytes<1024*1024?`${Math.max(1,Math.round(bytes/1024))} KiB`:`${(bytes/(1024*1024)).toFixed(1)} MiB`;

export default function Materials({course,lecture,csrf}:{course:string;lecture?:string;csrf:string}){
  const path=lecture?`/lectures/${lecture}/materials`:`/courses/${course}/materials`;
  const [rows,setRows]=useState<Material[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const [kind,setKind]=useState('syllabus'),[selectedFile,setSelectedFile]=useState<File|null>(null);
  const input=useRef<HTMLInputElement|null>(null),pending=useRef<{body:string;key:string}|null>(null);
  const load=useCallback(async()=>{const response=await fetch(`/api${path}`,{cache:'no-store'});if(!response.ok)throw new Error('Could not load saved materials.');setRows(await response.json());},[path]);
  useEffect(()=>{void load().catch(e=>setError(e instanceof Error?e.message:'Could not load saved materials.'));},[load]);
  function chooseFile(file:File|null){setError('');setNotice('');if(file&&file.size>MAX_BYTES){setSelectedFile(null);if(input.current)input.current.value='';setError('Choose a file up to 8 MiB.');return;}setSelectedFile(file);}
  async function upload(event:FormEvent){
    event.preventDefault();
    if(!selectedFile){setError('Choose a syllabus, curriculum, or slide file first.');return;}
    setBusy(true);setError('');setNotice('');
    try{
      const file=selectedFile;
      const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]??'');reader.onerror=()=>reject(new Error('The file could not be read.'));reader.readAsDataURL(file);});
      const body=JSON.stringify({name:file.name,kind,data,expected_count:rows.length});
      if(pending.current?.body!==body)pending.current={body,key:crypto.randomUUID()};
      const response=await fetch(`/api${path}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':pending.current.key},body});
      const result=await response.json().catch(()=>null);
      if(!response.ok){if(response.status===409){pending.current=null;await load();}throw new Error(result?.error?.message??'Upload failed. Try again.');}
      pending.current=null;setSelectedFile(null);if(input.current)input.current.value='';await load();setNotice('Saved. The readable text is now available as source evidence for this course.');
    }catch(e){setError(e instanceof Error?e.message:'Upload failed.');}finally{setBusy(false);}
  }
  const inputId=`material-file-${lecture?'lecture':'course'}`;
  return <section className="materials-panel" aria-labelledby={`${inputId}-title`}>
    <div className="materials-heading section-row"><div><p className="eyebrow">{lecture?'LECTURE SOURCES':'COURSE SOURCES'}</p><h2 id={`${inputId}-title`}>{lecture?'Lecture materials':'Syllabus and course materials'}</h2></div><span className="materials-count">{rows.length}/20 saved</span></div>
    <p className="materials-intro">{lecture?'Add the slides or handouts that belong to this lecture.':'Add the syllabus once and it will be available to this course’s lectures.'} These sources help your notes keep terminology, structure and important qualifications in view.</p>
    <div className="materials-guidance"><span className="materials-guidance-icon" aria-hidden="true">i</span><p><strong>What gets read</strong> Text from PPTX, DOCX, PDF, TXT and Markdown files is extracted and retained. Images, diagrams, embedded objects and speaker notes are not interpreted yet.</p></div>
    <form className="materials-uploader" onSubmit={upload}>
      <div className="materials-step"><span className="materials-step-number">1</span><div className="materials-step-body"><label htmlFor={`${inputId}-kind`}>Choose the source type</label><p className="small muted">This helps keep your library organized.</p><select id={`${inputId}-kind`} value={kind} disabled={busy} onChange={event=>setKind(event.target.value)}><option value="syllabus">Syllabus</option><option value="curriculum">Curriculum or reading guide</option><option value="slides">Lecture slides</option></select></div></div>
      <div className="materials-step"><span className="materials-step-number">2</span><div className="materials-step-body"><label htmlFor={inputId}>Choose a file</label><p className="small muted">Maximum 8 MiB. You can review the extracted text after saving.</p><input ref={input} id={inputId} type="file" accept=".pptx,.docx,.pdf,.txt,.md" disabled={busy} onChange={event=>chooseFile(event.target.files?.[0]??null)}/>{selectedFile?<div className="selected-material"><span className="selected-material-icon" aria-hidden="true">↗</span><span><strong>{selectedFile.name}</strong><small>{size(selectedFile.size)}</small></span><button type="button" className="text-button" disabled={busy} onClick={()=>chooseFile(null)}>Remove</button></div>:<div className="materials-empty-file">No file selected yet</div>}</div></div>
      <div className="materials-actions"><button type="submit" className="primary" disabled={busy||!selectedFile}>{busy?'Reading and saving…':'Save material'}</button><span className="small muted">Files stay in your private local workspace.</span></div>
    </form>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status" className="inline-notice">{notice}</p>}
    <div className="materials-library"><div className="section-row"><div><p className="eyebrow">SAVED SOURCES</p><h3>{rows.length?'Review your materials':'Your materials will appear here'}</h3></div>{rows.length>0&&<span className="small muted">{rows.length} source{rows.length===1?'':'s'}</span>}</div>
      {rows.length===0?<div className="materials-library-empty"><span aria-hidden="true">□</span><p>No files saved yet.</p><small>Add a syllabus or slide deck above to give your notes more context.</small></div>:<div className="material-list">{rows.map(row=><article className="material-card" key={row.id}><div className="material-card-heading"><div><p className="eyebrow">{kindLabels[row.kind]??row.kind}</p><h4>{row.name}</h4></div><span className="material-badge">{row.pages.length} {row.pages.length===1?'page':'pages'} read</span></div><div className="material-card-footer"><span className="small muted">Original file retained</span><a className="text-button" href={`/api/courses/${encodeURIComponent(course)}/materials/${encodeURIComponent(row.id)}/download`} download={row.name}>Download original ↗</a></div><details className="material-preview"><summary>Review extracted text</summary>{row.pages.map((page,index)=><div className="material-page" key={`${row.id}-${index}`}><h5>{page.label}</h5><p className="study-text">{page.text||'No readable text. Visual content has not been interpreted.'}</p></div>)}</details></article>)}</div>}
    </div>
  </section>;
}
