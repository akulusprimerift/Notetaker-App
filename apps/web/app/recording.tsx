'use client';
import {useEffect,useRef,useState} from 'react';
// The same browser-native module is exercised directly by the capture verification page.
// @ts-expect-error JavaScript module has no generated declaration file.
import {Recorder} from '../public/capture/recorder.mjs';

type Chunk={chunk_id:string;sequence:number;storage_state:string;start_sample:number;sample_count:number;released?:boolean};
type Run={id:string;state:string;sample_rate:number;saved_through_samples:number;complete:boolean;sealed:boolean;gaps:{reason:string}[];chunks:Chunk[]};
type LocalRun={id:string;pending_bytes:number;samples:number;sample_rate:number;stopped:boolean;server_sealed:boolean;persistent?:boolean;admitted?:boolean};
type State={active:boolean;working:boolean;message:string;local:LocalRun[];server:{available:boolean;capture_epoch:number;keep_audio?:boolean;runs:Run[]};emergency:{url:string;name:string}[]};
const duration=(samples:number,rate:number)=>{const seconds=Math.floor(samples/rate);return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;};
const bytes=(value:number)=>`${(value/1024/1024).toFixed(1)} MB`;

export default function Recording({owner,lecture,csrf,onBusy,compact=false}:{owner:string;lecture:string;csrf:string;onBusy:(value:boolean)=>void;compact?:boolean}) {
  const recorder=useRef<InstanceType<typeof Recorder>|null>(null);
  const selectedDevice=useRef('');
  const [state,setState]=useState<State>({active:false,working:false,message:'Checking recording readiness…',local:[],server:{available:false,capture_epoch:0,runs:[]},emergency:[]});
  const [devices,setDevices]=useState<MediaDeviceInfo[]>([]);
  const [deviceId,setDeviceId]=useState('');
  const [takeover,setTakeover]=useState(false);
  const [audio,setAudio]=useState<string|null>(null);
  const [retention,setRetention]=useState('');
  async function keepAudio(keep:boolean){
    setRetention('Saving…');
    try{
      const response=await fetch(`/api/lectures/${lecture}/audio-retention`,{method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({keep_audio:keep})});
      if(!response.ok)throw new Error((await response.json().catch(()=>null))?.error?.message??'Audio retention was not changed.');
      await recorder.current?.refresh();setRetention('');
    }catch(error){setRetention(error instanceof Error?error.message:'Audio retention was not changed.');}
  }
  useEffect(()=>{
    const instance=new Recorder({owner,lecture,csrf,onChange:(value:State)=>{setState(value);onBusy(value.active||value.working||value.emergency.length>0);},streamFactory:()=>navigator.mediaDevices.getUserMedia({audio:{deviceId:selectedDevice.current?{exact:selectedDevice.current}:undefined,channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false})});
    recorder.current=instance;void instance.init();
    return()=>{void instance.dispose();onBusy(false);};
  },[owner,lecture,csrf,onBusy]);
  useEffect(()=>{
    const refreshDevices=async()=>{
      if(!navigator.mediaDevices?.enumerateDevices)return;
      const rows=await navigator.mediaDevices.enumerateDevices();
      setDevices(rows.filter(row=>row.kind==='audioinput'));
    };
    void refreshDevices();
    navigator.mediaDevices?.addEventListener('devicechange',refreshDevices);
    return()=>navigator.mediaDevices?.removeEventListener('devicechange',refreshDevices);
  },[]);
  function chooseDevice(value:string){selectedDevice.current=value;setDeviceId(value);}
  const activeRun=state.server.runs.find(run=>run.state==='recording');
  const pending=state.local.reduce((sum,run)=>sum+run.pending_bytes,0);
  const local=state.local.find(run=>!run.stopped);
  const unresolved=state.local.filter(run=>!run.server_sealed||run.pending_bytes);
  const recoveryIds=[...new Set([...unresolved.map(run=>run.id),...state.server.runs.filter(run=>!run.sealed||!run.complete).map(run=>run.id)])];
  return <section className={`capture-panel ${compact?'capture-panel-compact':''}`} aria-labelledby="capture-title">
    <div className="section-row"><h2 id="capture-title">Lecture recording</h2><span className={state.active?'recording-badge':'prepared-badge'}>{state.active?'● Recording':'Saved audio → Study notes'}</span></div>
    {!compact&&<p className="muted">Capture your lecturer’s explanations and worked examples. Audio stays on this device. Saved audio can be transcribed below. Choose your note model below to turn the transcript into study notes.</p>}
    <div className="capture-controls">
      <label className="capture-device">Input<select aria-label="Recording input" value={deviceId} disabled={state.active||state.working} onChange={event=>chooseDevice(event.target.value)}><option value="">Default microphone</option>{devices.map(device=><option key={device.deviceId} value={device.deviceId}>{device.label||'Microphone '+device.deviceId.slice(0,6)}</option>)}</select></label>
      {state.active?<><strong className="capture-clock">{local?duration(local.samples,local.sample_rate):'0:00'}</strong><button className="primary" onClick={()=>void recorder.current?.stop()}>■ Stop recording</button></>:
        <button className="primary" disabled={state.working||state.emergency.length>0||!state.server.available||unresolved.length>0||!!activeRun} onClick={()=>void recorder.current?.start()}>● {state.server.runs.length?'Record another segment':'Start recording'}</button>}
      {!state.active&&activeRun&&<button className="secondary" disabled={state.working} onClick={()=>setTakeover(true)}>Take over recording</button>}
      <span className="small muted">{pending?`${bytes(pending)} held in this browser, awaiting confirmation`:'No audio waiting in the browser'}</span>
    </div>
    <p role="status" className="capture-message">{state.message}</p>
    {state.server.available&&<label className="cloud-consent"><input type="checkbox" checked={!!state.server.keep_audio} disabled={retention==='Saving…'} onChange={event=>void keepAudio(event.target.checked)}/><span>Keep lecture audio after transcription. {state.server.keep_audio?'Audio stays saved for playback until you finish or remove it.':'Each passage’s audio is deleted once it is transcribed, saving storage; the transcript and notes stay. Audio already deleted cannot be restored.'}</span></label>}
    {retention&&<p role="status" className="small muted">{retention}</p>}
    {typeof window!=='undefined'&&window.desktopApp?.platform==='darwin'&&!state.active&&<button className="text-button" onClick={()=>void window.desktopApp?.openMicrophoneSettings().catch(()=>setState(current=>({...current,message:'Open System Settings → Privacy & Security → Microphone. Enable Notetaker, then quit and reopen the app.'})))}>Microphone Settings</button>}
    {!compact&&typeof window!=='undefined'&&window.desktopApp?.platform==='darwin'&&<p className="small muted">Closing the window keeps recording. Reopen it from the Dock. Sleep interrupts capture; start another segment after waking. Stop recording and wait for confirmed saves before Quit.</p>}
    {compact&&(state.emergency.length>0||recoveryIds.length>0)&&<p className="small recovery-hint">Open the Capture tab to review recovery actions and saved segments.</p>}
    {!compact&&<>
      {state.local.some(run=>run.persistent===false)&&<p className="small muted">The browser did not grant protection against automatic storage clearing. Keep this page open until all audio is confirmed saved.</p>}
      {!state.server.available&&<p className="small muted">Use the Docker application with audio storage running to record. The SQLite preview does not capture audio.</p>}
      {state.emergency.map(item=><p key={item.url} className="error"><a href={item.url} download={item.name}>Download unsaved audio — {item.name}</a></p>)}
      {state.emergency.length>0&&!state.working&&<button className="secondary" onClick={()=>recorder.current?.releaseEmergency()}>I have saved all emergency downloads</button>}
      {!state.active&&recoveryIds.length>0&&<div className="recovery-box"><h3>Audio to recover</h3><p>Recovery stops the previous recording owner and saves the available segment. An unknown interruption stays marked. Keep the original browser open if it holds missing audio.</p>{recoveryIds.map(id=><button className="secondary" key={id} disabled={state.working} onClick={()=>void recorder.current?.recover(id)}>{state.server.runs.some(run=>run.id===id)?`Recover segment ${state.server.runs.findIndex(run=>run.id===id)+1}`:'Recover recording setup'}</button>)}{unresolved.filter(run=>run.admitted===false&&run.samples===0&&run.pending_bytes===0).map(run=><button className="secondary" key={`cancel-${run.id}`} disabled={state.working} onClick={()=>void recorder.current?.cancelSetup(run.id)}>Cancel unused setup</button>)}</div>}
      {takeover&&<div className="recovery-box" role="group" aria-label="Confirm recording takeover"><h3>Start a new segment here?</h3><p>The previous recorder will be blocked from further live saves. Stop it on the other device too; recover its buffered audio separately.</p><button className="primary" disabled={state.working} onClick={()=>{setTakeover(false);void recorder.current?.start(true);}}>Take over and start</button> <button className="secondary" onClick={()=>setTakeover(false)}>Cancel</button></div>}
      {state.server.runs.length>0&&<ol className="recording-segments">{state.server.runs.map((run,index)=><li key={run.id}>
      <div><strong>Segment {index+1}</strong><p>{duration(run.saved_through_samples,run.sample_rate)} confirmed continuously from this segment’s start · {run.complete?'All declared audio saved':run.state==='recording'?'Recording open':'Audio still pending'}</p>{run.gaps.length>0&&<p className="gap-notice">Interruption or separate segment boundary recorded. Missing time is not counted as saved audio.</p>}</div>
      {run.chunks.some(chunk=>chunk.released)&&<p className="small muted">{duration(run.chunks.filter(chunk=>chunk.released).reduce((sum,chunk)=>sum+chunk.sample_count,0),run.sample_rate)} of transcribed audio was deleted to save storage.</p>}
      {run.chunks.some(chunk=>chunk.storage_state==='verified'&&!chunk.released)&&<details><summary>Listen to saved audio</summary><div className="audio-parts">{run.chunks.filter(chunk=>chunk.storage_state==='verified'&&!chunk.released).map(chunk=><button className="text-button" key={chunk.chunk_id} onClick={()=>setAudio(`/api/lectures/${lecture}/audio-chunks/${chunk.chunk_id}`)}>Play {duration(chunk.start_sample,run.sample_rate)}–{duration(chunk.start_sample+chunk.sample_count,run.sample_rate)}</button>)}</div></details>}
      </li>)}</ol>}
      {audio&&<audio className="audio-player" controls autoPlay src={audio}>Your browser does not support audio playback.</audio>}
    </>}
  </section>;
}
