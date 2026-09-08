'use client';
import LiveUpdates from './live';

import {FormEvent, useCallback, useEffect, useRef, useState} from 'react';
import Recording from './recording';
import Transcript from './transcript';
import Notes from './notes';

type Course={id:string;name:string;code:string;created_at:string};
type Lecture={id:string;course_id:string;title:string;status:string;created_at:string;update_cursor:number};
type Snapshot={lecture:Lecture;course_name:string;settings:{depth:string;format:string};processing_location:string};
type Session={csrf_token:string;preview:boolean;owner_id:string};
class ApiError extends Error {constructor(message:string, public status:number){super(message)}}
async function request<T>(path:string, init:RequestInit={}):Promise<T>{
  let response:Response;
  try{response=await fetch(`/api${path}`,{...init,cache:'no-store',headers:{'Content-Type':'application/json',...init.headers}})}
  catch{throw new ApiError('The workspace could not be reached. Your form is still here; try again.',0)}
  if(!response.ok){const body=await response.json().catch(()=>null);throw new ApiError(body?.error?.message??'The workspace is unavailable. Make sure it is running, then try again.',response.status)}
  return response.status===204?undefined as T:response.json();
}
const date=(value:string)=>new Date(value).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
const initial=(name:string)=>name.trim().slice(0,1).toUpperCase();

export default function Workspace(){
  const [session,setSession]=useState<Session|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [captureBusy,setCaptureBusy]=useState(false);
  const [transcriptBusy,setTranscriptBusy]=useState(false);
  const sessionExpired=useCallback(()=>setSession(null),[]);
  const [code,setCode]=useState('');
  const [courses,setCourses]=useState<Course[]>([]);
  const [route,setRoute]=useState('');
  const [lectures,setLectures]=useState<Lecture[]>([]);
  const [snapshot,setSnapshot]=useState<Snapshot|null>(null);
  const [viewLoading,setViewLoading]=useState(false);
  const [form,setForm]=useState<'course'|'lecture'|null>(null);
  const [name,setName]=useState('');
  const [courseCode,setCourseCode]=useState('');
  const [notice,setNotice]=useState('');
  const formRef=useRef<HTMLDivElement>(null);
  const firstField=useRef<HTMLInputElement>(null);
  const returnFocus=useRef<HTMLElement|null>(null);
  const command=useRef<{payload:string;key:string}|null>(null);
  const selectedId=route.startsWith('course/')?route.slice(7):snapshot?.lecture.course_id;
  const selected=courses.find(c=>c.id===selectedId);

  const report=useCallback((err:unknown)=>{
    if(err instanceof ApiError&&err.status===401)setSession(null);
    setError(err instanceof Error?err.message:'Something went wrong. Try again.');
  },[]);
  const load=useCallback(async()=>{
    setLoading(true);setError('');
    try{const info=await request<Session>('/session');setSession(info);setCourses(await request<Course[]>('/courses'))}
    catch(err){if(err instanceof ApiError&&err.status===401)setSession(null);else report(err)}
    finally{setLoading(false)}
  },[report]);
  useEffect(()=>{void load();const changed=()=>{setRoute(location.hash.slice(1));setError('');setNotice('')};changed();window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed)},[load]);
  useEffect(()=>{
    if(!session)return;
    let active=true;setSnapshot(null);setLectures([]);
    if(!route){setViewLoading(false);return;}
    setViewLoading(true);
    const work=async()=>{
      try{
        if(route.startsWith('course/')){const rows=await request<Lecture[]>(`/courses/${encodeURIComponent(route.slice(7))}/lectures`);if(active)setLectures(rows)}
        else if(route.startsWith('lecture/')){const row=await request<Snapshot>(`/lectures/${encodeURIComponent(route.slice(8))}/snapshot`);if(active)setSnapshot(row)}
        else if(active)setError('This page is unavailable. Return to your library.');
      }catch(err){if(active)report(err)}finally{if(active)setViewLoading(false)}
    };void work();return()=>{active=false};
  },[route,session,report]);
  useEffect(()=>{if(form)firstField.current?.focus()},[form]);

  async function unlock(event:FormEvent){
    event.preventDefault();setBusy(true);setError('');
    try{const info=await request<Session>('/session/bootstrap',{method:'POST',body:JSON.stringify({token:code})});setCode('');setSession(info);setCourses(await request<Course[]>('/courses'))}catch(err){report(err)}finally{setBusy(false)}
  }
  function openForm(kind:'course'|'lecture'){
    if(captureBusy||transcriptBusy)return;
    returnFocus.current=document.activeElement as HTMLElement;setError('');setName('');setCourseCode('');command.current=null;setForm(kind);
  }
  function closeForm(){setForm(null);setError('');returnFocus.current?.focus()}
  async function save(event:FormEvent){
    event.preventDefault();if(!session)return;setBusy(true);setError('');
    const payload=JSON.stringify(form==='course'?{name:name.trim(),code:courseCode.trim()}:{title:name.trim()});
    if(command.current?.payload!==payload)command.current={payload,key:crypto.randomUUID()};
    try{
      const path=form==='course'?'/courses':`/courses/${selectedId}/lectures`;
      const row=await request<Course|Lecture>(path,{method:'POST',headers:{'X-CSRF-Token':session.csrf_token,'Idempotency-Key':command.current.key},body:payload});
      if(form==='course')setCourses(await request<Course[]>('/courses'));
      const destination=form==='course'?`course/${row.id}`:`lecture/${row.id}`;
      command.current=null;setForm(null);location.hash=destination;
    }catch(err){report(err)}finally{setBusy(false)}
  }
  async function logout(){
    if(!session||captureBusy||transcriptBusy)return;setBusy(true);
    try{await request('/session/logout',{method:'POST',headers:{'X-CSRF-Token':session.csrf_token}});setSession(null);setCourses([]);setSnapshot(null);setForm(null);setNotice('Workspace locked. Use a new local unlock code to return.')}catch(err){report(err)}finally{setBusy(false)}
  }

  if(loading)return <main className="loading"><span className="brand-icon">n</span><p role="status">Opening your workspace…</p></main>;
  if(!session)return <main className="welcome">
    <div className="welcome-story"><a className="brand" href="#"><span className="brand-icon">n</span>notetaker<span className="brand-dot">.</span></a><div><p className="eyebrow">YOUR LECTURES, KEPT CLOSE</p><h1>A place for<br/>everything<br/>you learn.</h1><p className="welcome-copy">Keep your courses together. Return to the ideas that matter. Build a library you can study from.</p></div><p className="local-note"><span className="status-dot"/>Private workspace · On this device</p></div>
    <section className="unlock-card"><p className="eyebrow">WELCOME TO YOUR WORKSPACE</p><h2>Make yourself at home.</h2><p className="muted">Enter the one-use code created by the local start command. This keeps your library private on this device.</p>
      {notice&&<p role="status" className="inline-notice">{notice}</p>}
      {error&&<p role="alert" className="error">{error}</p>}
      <form onSubmit={unlock}><label htmlFor="unlock-code">Workspace code</label><input id="unlock-code" type="password" autoComplete="off" required minLength={32} maxLength={200} value={code} onChange={e=>setCode(e.target.value)} placeholder="Paste your one-use code"/><button className="primary full" disabled={busy}>{busy?'Opening…':'Open workspace'}<span aria-hidden="true">↗</span></button></form>
      <p className="small muted">The code expires after 30 minutes and can only be used once. Your courses stay saved when the workspace closes.</p><button className="text-button" onClick={()=>void load()} disabled={busy}>Check connection again</button>
    </section>
  </main>;

  return <div className="workspace">
    <a className="skip" href="#main-content" onClick={event=>{event.preventDefault();document.getElementById('main-content')?.focus()}}>Skip to content</a>
    <aside className="sidebar"><a className="brand" href="#"><span className="brand-icon">n</span>notetaker<span className="brand-dot">.</span></a>
      <nav aria-label="Workspace"><a href="#" className={`nav-library ${!route?'active':''}`}><span aria-hidden="true">▦</span> Your library</a><div className="nav-title"><span>YOUR COURSES</span><button aria-label="Add a course" onClick={()=>openForm('course')}>+</button></div>
        {courses.length===0?<p className="sidebar-empty">Your courses will appear here.</p>:courses.map(course=><a key={course.id} href={`#course/${course.id}`} className={`course-link ${selectedId===course.id?'active':''}`}><span className="course-initial">{initial(course.name)}</span><span>{course.name}</span></a>)}
      </nav><div className="sidebar-bottom"><div className="local-note"><span className="status-dot"/>Local workspace</div><p>Saved on this device</p><button onClick={()=>void logout()} disabled={busy||captureBusy||transcriptBusy} className="text-button">Lock workspace</button></div>
    </aside>
    <div className="workspace-body"><div className="topbar"><span>YOUR SPACE TO LEARN</span><button className="text-button mobile-lock" onClick={()=>void logout()} disabled={busy||captureBusy||transcriptBusy}>Lock workspace</button><span className="privacy-badge"><span className="status-dot"/>{session.preview?'Local preview':'Private library'}</span></div>
    <main id="main-content" tabIndex={-1}>
      <div className="preview-notice">{session.preview?'Local preview · ':''}Your model takes notes from the lecture. Review the ideas, check the sources, and keep learning.</div>
      {error&&!form&&<div className="error" role="alert">{error} <a href="#">Return to library</a></div>}
      {viewLoading?<p role="status" className="page-loading">Opening lecture library…</p>:snapshot?<>
        <a className="back-link" href={`#course/${snapshot.lecture.course_id}`}>← {snapshot.course_name}</a>
        <div className="page-heading"><div><p className="eyebrow">LECTURE WORKSPACE</p><h1>{snapshot.lecture.title}</h1><p className="muted">Created {date(snapshot.lecture.created_at)} <span className="separator">/</span> Saved to your course</p></div><span className="prepared-badge">Saved workspace</span></div>
        <Recording owner={session.owner_id} lecture={snapshot.lecture.id} csrf={session.csrf_token} onBusy={setCaptureBusy}/>
        <LiveUpdates key={snapshot.lecture.id+'-live'} lecture={snapshot.lecture.id} onSessionExpired={sessionExpired}/>
        <Notes key={snapshot.lecture.id+'-notes'} lecture={snapshot.lecture.id} csrf={session.csrf_token} onSessionExpired={sessionExpired}/>
        <Transcript key={snapshot.lecture.id} owner={session.owner_id} lecture={snapshot.lecture.id} csrf={session.csrf_token} onBusy={setTranscriptBusy} onSessionExpired={sessionExpired}/>
      </>:route.startsWith('course/')&&selected?<>
        <a className="back-link" href="#">← Your library</a><div className="page-heading"><div><p className="eyebrow">{selected.code||'YOUR COURSE'}</p><h1>{selected.name}</h1><p className="muted">Your lectures, together in one place.</p></div><button className="primary" onClick={()=>openForm('lecture')}>+ New lecture</button></div>
        <div className="section-row"><h2>Lectures <span className="count">{lectures.length}</span></h2><span>Most recent first</span></div>
        {lectures.length===0?<section className="empty-state"><span className="empty-art" aria-hidden="true">≡</span><p className="eyebrow">START WITH A LECTURE</p><h2>Your next idea belongs here.</h2><p>Create a lecture to give your next class a home.<br/>You can reopen it any time.</p><button className="secondary" onClick={()=>openForm('lecture')}>Create your first lecture <span aria-hidden="true">↗</span></button></section>:<div className="lecture-list">{lectures.map(lecture=><a className="lecture-row" key={lecture.id} href={`#lecture/${lecture.id}`}><span className="lecture-icon" aria-hidden="true">≡</span><div><h3>{lecture.title}</h3><p>{date(lecture.created_at)} · {lecture.status==='prepared'?'No recording yet':'Open transcript and study notes'}</p></div><span className="prepared-badge">{lecture.status==='prepared'?'Prepared':lecture.status==='recording'?'Recording open':'Saved audio'}</span><span aria-hidden="true">↗</span></a>)}</div>}
      </>:!route?<>
        <div className="page-heading"><div><p className="eyebrow">A LITTLE STRUCTURE. MORE ROOM TO THINK.</p><h1>Your lecture library.</h1><p className="muted">Keep each course close. Pick up where you left off.</p></div><button className="primary" onClick={()=>openForm('course')}>+ New course</button></div>
        <div className="section-row"><h2>Your courses <span className="count">{courses.length}</span></h2><span>Only visible to you</span></div>
        {courses.length===0?<section className="empty-state"><span className="empty-art" aria-hidden="true">▤</span><p className="eyebrow">A LIBRARY THAT GROWS WITH YOU</p><h2>Every great set of notes starts somewhere.</h2><p>Add your first course. Then give each lecture its own<br className="desktop-break"/> space for the ideas, examples and details worth keeping.</p><button className="secondary" onClick={()=>openForm('course')}>Add your first course <span aria-hidden="true">↗</span></button></section>:<div className="course-grid">{courses.map((course,i)=><a className={`course-card tone-${i%3}`} href={`#course/${course.id}`} key={course.id}><span className="card-icon">{initial(course.name)}</span><span className="card-arrow" aria-hidden="true">↗</span><p className="eyebrow">{course.code||'COURSE'}</p><h2>{course.name}</h2><div className="card-footer"><span>Open lectures</span><span>Added {date(course.created_at)}</span></div></a>)}<button className="add-card" onClick={()=>openForm('course')}><span aria-hidden="true">+</span>Add another course</button></div>}
        <div className="library-footer"><span className="status-dot"/><p>Your library stays on this device. A little organization now makes coming back easier.</p></div>
      </>:null}
    </main></div>
    {form&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)closeForm()}}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="form-title" ref={formRef} onKeyDown={e=>{
      if(e.key==='Escape'&&!busy)closeForm();
      if(e.key==='Tab'){const fields=Array.from(formRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled)')??[]);const first=fields[0],last=fields.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}
    }}><div className="modal-heading"><p className="eyebrow">MAKE ROOM FOR WHAT'S NEXT</p><button aria-label="Close form" onClick={closeForm} disabled={busy}>×</button></div><h2 id="form-title">{form==='course'?'Add a course.':'Create a lecture.'}</h2><p className="muted">{form==='course'?'A home for all the lectures in one subject.':`This lecture will be saved in ${selected?.name??'your course'}.`}</p>{error&&<p role="alert" className="error">{error}</p>}<form onSubmit={save}><label htmlFor="name">{form==='course'?'Course name':'Lecture title'}</label><input id="name" ref={firstField} required maxLength={form==='course'?120:160} value={name} onChange={e=>setName(e.target.value)} placeholder={form==='course'?'e.g. Introduction to Biology':'e.g. Cell division and inheritance'} disabled={busy}/>{form==='course'&&<><label htmlFor="course-code">Course code <span className="muted">(optional)</span></label><input id="course-code" value={courseCode} maxLength={24} onChange={e=>setCourseCode(e.target.value)} placeholder="e.g. BIO 101" disabled={busy}/></>}<div className="form-actions"><button type="button" className="secondary" disabled={busy} onClick={closeForm}>Cancel</button><button className="primary" disabled={busy||!name.trim()}>{busy?'Saving…':form==='course'?'Create course':'Create lecture'}</button></div></form></div></div>}
  </div>;
}
