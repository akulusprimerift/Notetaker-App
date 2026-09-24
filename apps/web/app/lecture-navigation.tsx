'use client';
import {useLayoutEffect,useRef} from 'react';

type Tab<T extends string>={id:T;label:string;description:string};

export default function LectureNavigation<T extends string>({tabs,selected,onSelect}:{tabs:ReadonlyArray<Tab<T>>;selected:T;onSelect:(tab:T)=>void}){
  const navigation=useRef<HTMLElement>(null);
  const highlight=useRef<HTMLSpanElement>(null);
  useLayoutEffect(()=>{
    const nav=navigation.current,marker=highlight.current;
    if(!nav||!marker)return;
    const position=()=>{
      const active=nav.querySelector<HTMLElement>('[aria-selected="true"]');
      if(!active)return;
      marker.style.width=`${active.offsetWidth}px`;
      marker.style.height=`${active.offsetHeight}px`;
      marker.style.transform=`translate(${active.offsetLeft}px,${active.offsetTop}px)`;
      marker.style.opacity='1';
    };
    position();
    const observer=new ResizeObserver(position);
    observer.observe(nav);
    return()=>observer.disconnect();
  },[selected]);
  return <nav ref={navigation} className="lecture-tabs" aria-label="Lecture sections" role="tablist">
    <span ref={highlight} className="tab-highlight" aria-hidden="true"/>
    {tabs.map(tab=><button key={tab.id} role="tab" title={tab.description} aria-selected={selected===tab.id} className={selected===tab.id?'active':''} onClick={()=>onSelect(tab.id)}><span>{tab.label}</span></button>)}
  </nav>;
}
