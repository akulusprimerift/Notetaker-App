'use client';
import {useEffect,useRef,useState} from 'react';

type Speech={preview?:string;errors:string[];snapshot:{segments:{id:string;text:string;start_sample:number;sample_rate:number}[]}|null};
export default function TranscriptPreview({lecture,onSessionExpired,onOpen}:{lecture:string;onSessionExpired:()=>void;onOpen:()=>void}){
  const [speech,setSpeech]=useState<Speech|null>(null),[error,setError]=useState('');
  const panel=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    let alive=true,version=0;
    const live=(event:Event)=>{const detail=(event as CustomEvent).detail;if(detail.lecture===lecture){version++;setSpeech(detail.snapshot.transcript);setError('');}};
    window.addEventListener('lecture-snapshot',live);
    void (async()=>{const ticket=version;try{const response=await fetch(`/api/lectures/${lecture}/transcript`,{cache:'no-store'});if(!alive)return;if(response.status===401){onSessionExpired();return;}if(!response.ok)throw new Error();const data=await response.json();if(alive&&ticket===version)setSpeech(data);}catch{if(alive)setError('Waiting for live transcript connection…');}})();
    return()=>{alive=false;window.removeEventListener('lecture-snapshot',live);};
  },[lecture,onSessionExpired]);
  useEffect(()=>{if(panel.current)panel.current.scrollTop=panel.current.scrollHeight;},[speech]);
  return <section className="transcript-preview" aria-label="Live transcript preview"><div className="section-row"><h2>Live transcript</h2><button className="text-button" onClick={onOpen}>Open full transcript</button></div><p className="small muted">Follows new speech automatically. Draft words may change as recognition finishes.</p><div ref={panel} className="transcript-preview-scroll" tabIndex={0} role="region" aria-label="Latest recognized speech">
    {speech?.snapshot?.segments.slice(-30).map(p=><p key={p.id}><span className="small muted">{Math.floor(p.start_sample/p.sample_rate/60)}:{String(Math.floor(p.start_sample/p.sample_rate)%60).padStart(2,'0')} </span>{p.text}</p>)}
    {speech?.preview&&<p className="speech-draft"><strong>Transcribing now… </strong>{speech.preview}</p>}
    {error&&<p>{error}</p>}
    {!speech?.preview&&!speech?.snapshot?.segments.length&&<p className="muted">{speech?.errors.includes('model_unavailable')?'Select a speech model to transcribe your saved audio.':'Your lecturer’s words will appear here as saved audio is recognized.'}</p>}
  </div></section>;
}
