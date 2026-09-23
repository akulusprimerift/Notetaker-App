'use client';
import {useRef,useState} from 'react';

export type SpeechModelState={state:string;name:string|null};
const labels:Record<string,string>={missing:'No usable speech model selected',selected:'Speech model selected · readiness not yet confirmed',loading:'Loading speech model…',ready:'Speech model active · ready to transcribe',offline:'Speech worker unavailable · readiness not confirmed',failed:'Speech model could not load · select a compatible model'};
export default function SpeechModel({model}:{model:SpeechModelState|null}){
  const dialog=useRef<HTMLDialogElement>(null);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  async function choose(){
    if(!window.desktopApp){dialog.current?.showModal();return;}
    setBusy(true);setMessage('');
    try{const result=await window.desktopApp.chooseSpeech();if(result)setMessage(`${result.name} selected. ${result.restartRequired?'Finish recording and wait for confirmed saves, then quit and reopen Notetaker to activate it.':'Start local services to activate it.'}`);}
    catch(error){setMessage(error instanceof Error?error.message:'The model could not be selected. Try again.');}
    finally{setBusy(false);}
  }
  return <section className="speech-model" aria-label="Speech model"><div className="section-row"><p role="status"><strong>{model?labels[model.state]??labels.selected:'Checking speech model…'}</strong>{model?.name&&<span> · {model.name}</span>}</p><div className="editor-actions"><button className="secondary" disabled={busy} onClick={()=>void choose()}>{busy?'Finding local models…':'Select speech model'}</button><button className="text-button" onClick={()=>dialog.current?.showModal()}>How to get a model</button></div></div>{message&&<p role="status" className="small">{message}</p>}
    <dialog ref={dialog} className="accounts-dialog speech-help" aria-labelledby="speech-help-title"><header className="accounts-heading"><h2 id="speech-help-title">Set up speech recognition</h2><button className="secondary" autoFocus onClick={()=>dialog.current?.close()}>Close</button></header>
      <p>Speech models turn audio into text. Your note model is selected separately. Notetaker uses local faster-whisper files and never downloads a model automatically.</p>
      <p><a href="https://huggingface.co/Systran/faster-whisper-small.en/tree/main" target="_blank" rel="noreferrer" onClick={event=>{if(window.desktopApp){event.preventDefault();void window.desktopApp.openSpeechGuide().catch(()=>setMessage('Open huggingface.co/Systran/faster-whisper-small.en in your browser.'));}}}>Open speech-model download page ↗</a></p>
      <ol><li>In your browser, open <strong>huggingface.co/Systran/faster-whisper-small.en</strong> and choose <strong>Files and versions</strong>. This is an English speech model.</li><li>Download <strong>model.bin</strong>, <strong>config.json</strong>, <strong>tokenizer.json</strong> and <strong>vocabulary.txt</strong> into one folder named <strong>faster-whisper-small.en</strong>. Use each file’s download button; do not save the web page.</li><li><strong>Windows:</strong> keep that folder in Downloads or Models in your user folder. Click <strong>Select speech model</strong>; Notetaker looks there and in the Hugging Face cache and offers a model it finds. You can also browse to the folder.</li><li><strong>macOS preparation:</strong> use Safari and Finder to download the same files into one folder under Downloads. Keep it for the future macOS app; macOS app support is not available yet.</li><li>The files stay on your computer; there is no upload. If services are running, finish recording, wait for confirmed saves, then quit and reopen Notetaker. Look for <strong>Speech model active · ready to transcribe</strong> before expecting live text.</li></ol>
      <p className="small muted">Using the browser/Docker workspace? Set its speech-model folder through the Windows app’s Workspace settings or your local service configuration, then restart those services after recording. File detection alone does not confirm runtime compatibility.</p>
    </dialog>
  </section>;
}
