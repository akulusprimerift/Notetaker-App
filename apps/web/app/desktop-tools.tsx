'use client';
import {useEffect} from 'react';

export default function DesktopTools(){
  useEffect(()=>{if(window.desktopApp)document.documentElement.dataset.desktop=String(window.desktopApp.platform!=='darwin');},[]);
  if(typeof window==='undefined'||!window.desktopApp)return null;
  return <button type="button" className="secondary desktop-tools settings-action" onClick={()=>void window.desktopApp!.openSetup()} title="Open local services and model settings">Workspace setup</button>;
}
