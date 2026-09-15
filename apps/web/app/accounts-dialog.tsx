'use client';

import {useEffect,useRef,useState} from 'react';
import ProviderConnections from './provider-connections';

export default function AccountsDialog({csrf,onSessionExpired}:{csrf:string;onSessionExpired:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null);
  const [opened,setOpened]=useState(false);
  useEffect(()=>{
    const open=()=>{setOpened(true);dialog.current?.showModal();};
    window.addEventListener('open-accounts',open);
    return()=>window.removeEventListener('open-accounts',open);
  },[]);
  return <dialog ref={dialog} className="accounts-dialog" aria-labelledby="accounts-title" onClose={()=>setOpened(false)}>
    <header className="accounts-heading"><div><p className="eyebrow">WORKSPACE SETTINGS</p><h2 id="accounts-title">Accounts &amp; API keys</h2></div><button className="secondary" autoFocus onClick={()=>dialog.current?.close()}>Close</button></header>
    {opened&&<ProviderConnections csrf={csrf} onSessionExpired={onSessionExpired} onChanged={()=>{}}/>}
  </dialog>;
}
