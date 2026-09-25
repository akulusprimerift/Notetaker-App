'use client';
import {useEffect, useRef, useState, type ReactNode} from 'react';

/** Browser columns paginate the original text, including passages taller than a page. */
export default function NotePages({children}:{children:ReactNode}){
  const viewport=useRef<HTMLDivElement>(null), content=useRef<HTMLDivElement>(null);
  const [page,setPage]=useState(0),[count,setCount]=useState(1);
  const current=useRef(0);
  useEffect(()=>{
    const panel=viewport.current,flow=content.current;
    if(!panel||!flow)return;
    let disposed=false;
    const measure=()=>{
      if(disposed||!panel.clientWidth)return;
      flow.style.columnWidth=`${panel.clientWidth}px`;
      const pages=Math.max(1,Math.round(flow.scrollWidth/panel.clientWidth));
      const selected=Math.min(current.current,pages-1);
      setCount(pages);setPage(selected);current.current=selected;
      panel.scrollTo({left:selected*panel.clientWidth,behavior:'instant'});
    };
    const observer=new ResizeObserver(measure);observer.observe(panel);observer.observe(flow);
    const mutations=new MutationObserver(measure);mutations.observe(flow,{subtree:true,childList:true,characterData:true});
    const snap=()=>{
      const left=Math.round(panel.scrollLeft/panel.clientWidth)*panel.clientWidth;
      if(Math.abs(left-panel.scrollLeft)>1)panel.scrollTo({left,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
    };
    panel.addEventListener('scrollend',snap);
    measure();void document.fonts.ready.then(measure);
    return()=>{disposed=true;observer.disconnect();mutations.disconnect();panel.removeEventListener('scrollend',snap);};
  },[]);
  function go(next:number){
    const panel=viewport.current;if(!panel)return;
    const target=Math.max(0,Math.min(count-1,next));
    panel.scrollTo({left:target*panel.clientWidth,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  }
  return <section className="note-reader" aria-label="Paged lecture notes">
    <div className="note-page-heading"><strong role="status">Section {page+1} of {count}</strong><span className="small muted">Swipe sideways or choose a number</span></div>
    <div className="note-pages-viewport" ref={viewport} tabIndex={0} aria-label="Note sections; use left and right arrow keys" onKeyDown={event=>{
      if(event.target!==event.currentTarget)return;
      if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();go(event.key==='Home'?0:event.key==='End'?count-1:page+(event.key==='ArrowRight'?1:-1));}
    }} onScroll={event=>{const panel=event.currentTarget;const next=Math.min(count-1,Math.max(0,Math.round(panel.scrollLeft/panel.clientWidth)));current.current=next;setPage(next);}}>
      <div className="note-pages-flow" ref={content}>{children}</div>
    </div>
    <nav className="note-page-nav" aria-label="Note sections"><button className="secondary" disabled={page===0} onClick={()=>go(page-1)} aria-label="Previous note section">←</button><div className="note-page-numbers">{Array.from({length:count},(_,index)=><button key={index} className="secondary" aria-label={`Note section ${index+1}`} aria-current={page===index?'page':undefined} onClick={()=>go(index)}>{index+1}</button>)}</div><button className="secondary" disabled={page===count-1} onClick={()=>go(page+1)} aria-label="Next note section">→</button></nav>
  </section>;
}
