'use strict';
const {audioPermission}=require('./policy.cjs');
const MICROPHONE_SETTINGS='x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone';

async function requestMicrophone({contents,permission,details,platform,systemPreferences,dialog,window,shell}) {
  if(!audioPermission(contents,permission,details))return false;
  if(platform==='darwin'){
    let status=systemPreferences.getMediaAccessStatus('microphone');
    if(status==='not-determined'){
      await systemPreferences.askForMediaAccess('microphone');
      status=systemPreferences.getMediaAccessStatus('microphone');
    }
    if(status!=='granted'){
      const result=await dialog.showMessageBox(window,{type:'info',buttons:['Not now','Open Microphone Settings'],defaultId:0,cancelId:0,
        message:'Microphone access is unavailable.',detail:'Enable Notetaker in System Settings → Privacy & Security → Microphone, then quit and reopen Notetaker. Restrictions may require your administrator. Saved audio is retained.'});
      if(result.response===1)await shell.openExternal(MICROPHONE_SETTINGS);
      return false;
    }
  }else{
    const result=await dialog.showMessageBox(window,{type:'question',buttons:['Allow microphone','Cancel'],defaultId:1,cancelId:1,
      message:'Allow Notetaker to record your microphone for this lecture?'});
    if(result.response!==0)return false;
  }
  return audioPermission(contents,permission,details);
}

function restoreWindow(window){
  if(!window||window.isDestroyed())return;
  if(window.isMinimized())window.restore();
  window.show();window.focus();
}

function macMenu({showWorkspace,showSetup,quit}){
  return [
    {label:'Notetaker',submenu:[{role:'about'},{type:'separator'},
      {label:'Workspace Settings…',accelerator:'Command+,',click:showSetup},{type:'separator'},
      {role:'services'},{type:'separator'},{role:'hide'},{role:'hideOthers'},{role:'unhide'},
      {type:'separator'},{label:'Quit Notetaker',accelerator:'Command+Q',click:quit}]},
    {label:'File',submenu:[{role:'close'}]},
    {role:'editMenu'},
    {label:'View',submenu:[{role:'resetZoom'},{role:'zoomIn'},{role:'zoomOut'},{type:'separator'},{role:'togglefullscreen'}]},
    {label:'Window',submenu:[{role:'minimize'},{role:'zoom'},
      {label:'Show Workspace',click:showWorkspace},{type:'separator'},{role:'front'}]},
  ];
}

function bindPowerEvents(powerMonitor,send){
  const suspend=()=>send('suspend'),resume=()=>send('resume');
  powerMonitor.on('suspend',suspend);powerMonitor.on('resume',resume);
  return ()=>{powerMonitor.removeListener('suspend',suspend);powerMonitor.removeListener('resume',resume);};
}
module.exports={requestMicrophone,restoreWindow,macMenu,bindPowerEvents,MICROPHONE_SETTINGS};
