'use client';
import {useEffect,useState,type ReactNode} from 'react';
export default function ReviewNotice({lecture,revision,children}:{lecture:string;revision:string;children:ReactNode}){
  const key=`notetaker:review-hidden:${lecture}:${revision}`;
  const [hidden,setHidden]=useState(false);
  useEffect(()=>{try{setHidden(localStorage.getItem(key)==='yes');}catch{setHidden(false);}},[key]);
  function change(value:boolean){setHidden(value);try{if(value)localStorage.setItem(key,'yes');else localStorage.removeItem(key);}catch{/* The current window still remembers the choice. */}}
  return hidden?<button className="text-button" onClick={()=>change(false)}>Show review notices</button>:<section className="note-review"><div className="section-row"><h3>Worth reviewing</h3><button className="text-button" aria-label="Dismiss Worth reviewing" onClick={()=>change(true)}>Close ×</button></div>{children}</section>;
}
