'use client';
import {useRef,useState} from 'react';

export default function MarkMoment({lecture,csrf,run,sample,disabled=false}:{lecture:string;csrf:string;run:string;sample:number;disabled?:boolean}){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[failed,setFailed]=useState(false);
  const pending=useRef<{key:string;body:string}|null>(null);
  async function mark(){
    if(!pending.current)pending.current={key:crypto.randomUUID(),body:JSON.stringify({run_id:run,sample})};
    setBusy(true);setMessage('');
    try{
      const response=await fetch(`/api/lectures/${lecture}/study/marks`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':pending.current.key},body:pending.current.body});
      const result=await response.json();if(!response.ok)throw new Error(result.error?.message||'Could not save this marker.');
      pending.current=null;setFailed(false);setMessage('Marked important. Review it in Study tools.');window.dispatchEvent(new Event('study-marks-changed'));
    }catch(error){setFailed(true);setMessage(error instanceof Error?error.message:'Marker not saved. Retry when connected.');}
    finally{setBusy(false);}
  }
  return <div className="mark-moment"><button className="secondary" disabled={busy||(disabled&&!pending.current)} onClick={()=>void mark()}>{busy?'Saving marker…':failed?'Retry saving marker':'★ Mark Important'}</button>{message&&<span className="small" role={failed?'alert':'status'}>{message}</span>}</div>;
}
