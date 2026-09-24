'use client';
import {useEffect} from 'react';

export default function DesktopTools(){
  useEffect(()=>{if(window.desktopApp)document.documentElement.dataset.desktop='true';},[]);
  if(typeof window==='undefined'||!window.desktopApp)return null;
  return <button className="desktop-tools" onClick={()=>void window.desktopApp!.openSetup()} title="Open local services and model settings"><span aria-hidden="true">⚙</span><span>Workspace settings</span></button>;
}
