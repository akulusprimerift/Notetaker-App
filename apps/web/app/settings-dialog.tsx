'use client';

import {useEffect,useRef} from 'react';
import DataRemoval from './data-removal';
import DesktopTools from './desktop-tools';
import Theme from './theme';

type Props={owner:string;csrf:string;onRemoved:(lecture:string,kind:string)=>void};

export default function SettingsDialog({owner,csrf,onRemoved}:Props){
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{
    const open=()=>{if(!dialog.current?.open)dialog.current?.showModal();};
    window.addEventListener('open-settings',open);
    return()=>window.removeEventListener('open-settings',open);
  },[]);
  return <dialog ref={dialog} className="settings-dialog" aria-labelledby="settings-title">
    <div className="settings-content">
      <header className="settings-heading"><div><h2 id="settings-title">Settings</h2><p className="muted">Preferences for this workspace.</p></div><button type="button" className="secondary" autoFocus onClick={()=>dialog.current?.close()}>Close</button></header>
      <section className="settings-section" aria-labelledby="settings-appearance-title">
        <h3 id="settings-appearance-title">Appearance</h3>
        <Theme/>
        <p className="small muted settings-help">Your theme is saved on this device.</p>
      </section>
      <section className="settings-section" aria-labelledby="settings-workspace-title">
        <h3 id="settings-workspace-title">Workspace</h3>
        <button type="button" className="secondary settings-action" onClick={()=>window.dispatchEvent(new Event('open-accounts'))}>Accounts &amp; API keys</button>
        <DesktopTools/>
      </section>
      <section className="settings-section" aria-labelledby="settings-data-title">
        <h3 id="settings-data-title">Data controls</h3>
        <DataRemoval owner={owner} csrf={csrf} onRemoved={onRemoved}/>
      </section>
    </div>
  </dialog>;
}
