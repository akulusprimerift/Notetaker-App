'use strict';
const {app, BrowserWindow, dialog, ipcMain, session, shell} = require('electron');
const path = require('node:path');
const fs = require('node:fs/promises');
const {spawn} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {ORIGIN, localPage, audioPermission} = require('./policy.cjs');
const {discoverModels,discoverSpeechModels,validSpeechFolder} = require('./models.cjs');
const {findPowerShell} = require('./powershell.cjs');
const {ProviderBridge} = require('./provider-bridge.cjs');
const {NativeRuntime} = require('./native-runtime.cjs');

app.setName('Notetaker');
const explicitData = app.commandLine.getSwitchValue('user-data-dir');
if (explicitData && path.isAbsolute(explicitData)) app.setPath('userData', explicitData);
app.enableSandbox();
let window, setupWindow, providerBridge, bridgeConfig, quitting = false, starting = false, message = 'Checking local services…', speechPath = '', serviceRoot = '';
let appearance = 'light', autoStarting = false;
const palettes = {light:['#e0e1dd','#1b263b'],dark:['#090d17','#f2f2f5'],pink:['#ffe5ec','#4b1830'],blue:['#caf0f8','#03045e']};
function chromeOptions(){return {titleBarStyle:'hidden',titleBarOverlay:{color:palettes[appearance][0],symbolColor:palettes[appearance][1],height:40},backgroundColor:palettes[appearance][0],roundedCorners:true};}
let serviceMode = 'docker', nativeRuntime, shutdownComplete = false, shutdownStarted = false, speechRestartRequired = false, libraryChosen = false;
const nativeResources = () => app.isPackaged ? path.join(process.resourcesPath,'native-runtime') : process.env.NOTETAKER_NATIVE_RESOURCES;
async function nativeAvailable(){try{if(!nativeResources())return false;await fs.access(path.join(nativeResources(),'runtime-manifest.json'));return true;}catch{return false;}}
const setupURL = pathToFileURL(path.join(__dirname, 'setup.html')).href;
const runtime = () => app.isPackaged ? path.join(app.getPath('userData'), 'services') : path.resolve(__dirname, '../..');
const configPath = () => path.join(app.getPath('userData'), 'desktop-settings.json');
let configWrite=Promise.resolve();
function saveConfig() {
  const content=JSON.stringify({speechPath,serviceRoot,serviceMode,libraryChosen,appearance});
  configWrite=configWrite.catch(()=>{}).then(async()=>{
    await fs.writeFile(configPath()+'.tmp',content);
    await fs.rename(configPath()+'.tmp',configPath());
  });
  return configWrite;
}

async function healthStatus() {
  if(serviceMode==='native'&&!nativeRuntime?.ready)return false;
  try {
    const response = await fetch(ORIGIN + '/api/health', {signal:AbortSignal.timeout(2500), redirect:'error'});
    const data=await response.json();
    return {ok:response.ok&&data.status==='ok',providerBridgePort:data.provider_bridge_port};
  } catch { return false; }
}
async function healthy() {const status=await healthStatus();return status!==false&&status.ok;}
async function bridgeReady() {const status=await healthStatus();return status!==false&&status.ok&&(!bridgeConfig||status.providerBridgePort===bridgeConfig.port);}
async function setup() {
  await window.loadURL(setupURL);
}
async function showSetup() {
  if (window.webContents.getURL() === setupURL) {window.show();return;}
  if (setupWindow && !setupWindow.isDestroyed()) {setupWindow.show();return;}
  setupWindow = new BrowserWindow({...chromeOptions(),width:960,height:850,title:'Notetaker setup',
    webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true}});
  setupWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  setupWindow.webContents.on('will-navigate',(event,url)=>{if(url!==setupURL)event.preventDefault();});
  await setupWindow.loadURL(setupURL);
}
async function startServices(force=false) {
  if (starting) return;
  if(!libraryChosen&&await nativeAvailable())throw new Error('Choose a standalone library or an existing workspace folder first.');
  if(serviceMode==='native'){
    starting=true;message='Starting your standalone library…';
    try{
      if(!nativeResources())throw new Error('The standalone runtime is not bundled in this build.');
      nativeRuntime ||= new NativeRuntime({resources:nativeResources(),dataPath:app.getPath('userData'),
        safeStorage:require('electron').safeStorage,utilityProcess:require('electron').utilityProcess,
        onProgress:detail=>{message=detail;},
        onFailure:detail=>{message='Could not keep the standalone workspace running. '+detail;void nativeRuntime.stop();}});
      await nativeRuntime.start({speechPath,bridgeConfig});message='Your standalone workspace is ready.';
    }catch(error){message='Could not start the standalone workspace. '+error.message;}
    finally{starting=false;}
    return;
  }
  if (!force && await healthy()) {message='Your local workspace is ready.';return;}
  const powershell = await findPowerShell();
  if (!powershell) throw new Error('PowerShell 7 was not found. Install PowerShell 7, restart Notetaker, and try again.');
  if (app.isPackaged && !serviceRoot) {
    let configured=false;
    try {await fs.access(path.join(runtime(),'.local/services.env'));configured=true;} catch { /* First setup. */ }
    if(!configured) {
      const choice=await dialog.showMessageBox(setupWindow || window,{type:'question',buttons:['Cancel','Create new desktop library'],defaultId:0,cancelId:0,
        message:'Create a new desktop library?',detail:'To keep using an existing development library, cancel and choose its workspace folder in setup. A new desktop library uses separate Docker volumes.'});
      if(choice.response!==1)return;
    }
  }
  starting = true; message = 'Starting Docker services. First startup can take several minutes…';
  try {
    if (app.isPackaged) {
      await fs.mkdir(runtime(), {recursive:true});
      await fs.cp(path.join(process.resourcesPath, 'service-source'), runtime(), {recursive:true});
    }
    const args = ['-NoProfile', '-File', path.join(runtime(), 'scripts', 'Start-App.ps1')];
    if(serviceRoot)args.push('-WorkspacePath',serviceRoot);
    if ((await discoverModels({speechPath})).speech) args.push('-WithSpeech', '-SpeechModelPath', speechPath);
    const child = spawn(powershell, args, {cwd:runtime(), windowsHide:true,
      env:{...process.env, ...(bridgeConfig ? {NOTETAKER_PROVIDER_BRIDGE_URL:bridgeConfig.url,NOTETAKER_PROVIDER_BRIDGE_TOKEN:bridgeConfig.token} : {}),
        ...(app.isPackaged ? {COMPOSE_PROJECT_NAME:serviceRoot?'notetaker':'notetaker-desktop'} : {})}, stdio:['ignore','pipe','pipe']});
    // Logs stay on this device and do not contain supplied source text.
    let output = '';
    child.stdout.on('data', data => {output=(output+data.toString()).slice(-32000);});
    child.stderr.on('data', data => {output=(output+data.toString()).slice(-32000);});
    const code = await new Promise((resolve,reject) => {child.once('error',reject);child.once('exit',resolve);});
    await fs.writeFile(path.join(app.getPath('userData'),'startup.log'), output);
    if (code !== 0) throw new Error('Local service startup failed; details are in startup.log in the app data folder.');
    message = await healthy() ? 'Your local workspace is ready. Open the workspace to begin.' : 'Services started, but the workspace is not responding. Retry after checking Docker Desktop.';
  } catch (error) {
    message = 'Could not start the workspace. Check Docker Desktop (Linux containers), PowerShell 7 and available disk space. ' + error.message;
  } finally {starting=false;}
}

function authorize(event, allowWorkspace = false) {
  const exactWindow = [window, setupWindow].some(w => w && !w.isDestroyed() && event.sender === w.webContents && event.senderFrame === w.webContents.mainFrame);
  const allowedFrame = event.senderFrame.url === setupURL || (allowWorkspace && localPage(event.senderFrame.url));
  if (!exactWindow || !allowedFrame)
    throw new Error('This action is available only in Notetaker setup or workspace.');
}
function register(name, action, allowWorkspace = false) {ipcMain.handle(name, async (event) => {authorize(event, allowWorkspace);return action();});}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => {if(window){window.show();window.focus();}});
  app.whenReady().then(async () => {
    providerBridge = new ProviderBridge(app.getPath('userData'), require('electron').safeStorage, {openExternal:url=>require('electron').shell.openExternal(url), codexExecutable:app.isPackaged?path.join(process.resourcesPath,'account-client/bin/codex.exe'):path.join(__dirname,'../../node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe')});
    try {bridgeConfig=await providerBridge.start();}
    catch (error) {console.error('Provider bridge could not start:', error.message);bridgeConfig=null;}
    try {const config=JSON.parse(await fs.readFile(configPath(),'utf8'));appearance=typeof config.appearance==='string'&&Object.hasOwn(palettes,config.appearance)?config.appearance:'light';speechPath=config.speechPath || '';serviceRoot=config.serviceRoot || '';serviceMode=config.serviceMode==='native'?'native':'docker';libraryChosen=config.libraryChosen!==false;} catch { /* First launch. */ }
    if (!speechPath && !app.isPackaged) speechPath=path.join(runtime(),'.local/models/faster-whisper-small.en');
    window = new BrowserWindow({...chromeOptions(),width:1360,height:950,minWidth:760,minHeight:600,title:'Notetaker',show:false,icon:path.join(__dirname,'icon.ico'),
      webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true,webSecurity:true,backgroundThrottling:false}});
    session.defaultSession.setPermissionCheckHandler((contents, permission, origin) =>
      permission === 'media' && localPage(contents?.getURL() || '') && localPage(origin));
    session.defaultSession.setPermissionRequestHandler(async (contents, permission, callback, details) => {
      if (!audioPermission(contents, permission, details)) return callback(false);
      const result = await dialog.showMessageBox(window, {type:'question',buttons:['Allow microphone','Cancel'],defaultId:1,cancelId:1,
        message:'Allow Notetaker to record your microphone for this lecture?'});
      callback(result.response===0 && audioPermission(contents, permission, details));
    });
    window.webContents.setWindowOpenHandler(() => ({action:'deny'}));
    window.webContents.on('will-navigate', (event,url) => {if(!localPage(url) && url!==setupURL)event.preventDefault();});
    window.webContents.on('will-attach-webview', event => event.preventDefault());
    window.webContents.on('render-process-gone', () => {message='The workspace renderer stopped. Saved audio and recovery drafts remain on disk.';void setup();});
    window.on('close', event => {
      if(quitting)return;
      event.preventDefault();
      void dialog.showMessageBox(window, {type:'question',buttons:['Keep app open','Hide window','Quit app'],defaultId:0,cancelId:0,
        message:'Finish and save your recording before quitting.',detail:'Hide keeps recording and this workspace running. Quit closes the recorder; already journaled audio remains recoverable. '+(serviceMode==='native'?'Standalone processing pauses until you reopen the app.':'Docker services continue processing.')})
        .then(result => {if(result.response===1)window.hide();if(result.response===2){quitting=true;app.quit();}});
    });
    // Keep navigation inside the workspace. The default Electron menu bar is
    // intentionally removed so the desktop shell does not compete with the
    // lecture navigation.
    require('electron').Menu.setApplicationMenu(null);
    register('setup:status',async()=>({appearance,autoStarting,starting,message:starting?message:speechRestartRequired?'Speech model saved. Finish recording, then quit and reopen Notetaker to use it.':await healthy()?(!speechPath?'Audio saving is ready. Choose a speech model folder and restart services to enable transcription and automatic notes.':'Your local workspace is ready.'):message.startsWith('Could not')?message:serviceMode==='native'?'Standalone workspace is stopped. Start it to continue.':'Choose a standalone library or start your existing Docker workspace.',dataPath:app.getPath('userData'),serviceRoot,serviceMode,nativeAvailable:await nativeAvailable()}));
    register('setup:start',startServices);
    register('setup:native',async()=>{
      if(starting)throw new Error('Wait for startup to finish.');
      if(!nativeResources())throw new Error('Standalone services are unavailable in this build.');
      serviceMode='native';libraryChosen=true;await saveConfig();await startServices();
    });
    register('setup:stop-native',async()=>{
      if(starting)throw new Error('Wait for startup to finish.');
      if(!nativeRuntime?.host)return;
      const choice=await dialog.showMessageBox(setupWindow||window,{type:'question',buttons:['Keep running','Pause services'],defaultId:0,cancelId:0,
        message:'Finish recording and wait for confirmed saves before pausing.',detail:'This pauses the standalone workspace so you can change libraries or restart with a different speech model. Saved data is retained.'});
      if(choice.response!==1)return;
      starting=true;
      try{await nativeRuntime.stop();nativeRuntime=null;speechRestartRequired=false;message='Standalone services paused. You can change libraries or start again.';}
      finally{starting=false;}
    });
    register('setup:open',async()=>{if(!libraryChosen&&await nativeAvailable())throw new Error('Choose a library first.');if(!(await healthy()))throw new Error('Start local services first.');if(window.webContents.getURL()===setupURL)await window.loadURL(ORIGIN);window.show();if(setupWindow&&!setupWindow.isDestroyed())setupWindow.close();});
    register('setup:models',()=>discoverModels({speechPath,ollamaURL:serviceMode==='native'?'http://127.0.0.1:11435':'http://127.0.0.1:11434'}));
    register('setup:workspace-folder',async()=>{
      if(starting)throw new Error('Wait for service startup to finish before changing workspace.');
      if(nativeRuntime?.host)throw new Error('Pause standalone services before changing libraries.');
      const chosen=await dialog.showOpenDialog(setupWindow || window,{properties:['openDirectory'],title:'Choose the existing Notetaker workspace folder'});
      if(chosen.canceled)return;
      const folder=chosen.filePaths[0];
      for(const item of ['compose.yaml','.local/services.env','.local/s3.json']){
        try {await fs.access(path.join(folder,item));} catch {throw new Error('Choose the original workspace folder containing compose.yaml and its existing .local service configuration.');}
      }
      serviceRoot=folder;serviceMode='docker';libraryChosen=true;
      if(!speechPath)speechPath=path.join(folder,'.local/models/faster-whisper-small.en');
      await saveConfig();
    });
    const chooseSpeech=async()=>{
      const candidates=await discoverSpeechModels({selected:speechPath,roots:[path.join(runtime(),'.local','models')]});
      let folder='';
      if(candidates.length){
        const choice=await dialog.showMessageBox(setupWindow||window,{type:'question',message:'Local speech model found',detail:candidates[0],buttons:['Use this model','Browse for another','Cancel'],defaultId:0,cancelId:2});
        if(choice.response===2)return null;
        if(choice.response===0)folder=candidates[0];
      }
      const chosen=folder?{canceled:false,filePaths:[folder]}:await dialog.showOpenDialog(setupWindow||window,{properties:['openDirectory'],defaultPath:speechPath||app.getPath('downloads'),title:'Select the folder containing model.bin, config.json and tokenizer.json'});
      if(chosen.canceled)return;
      if(!await validSpeechFolder(chosen.filePaths[0]))throw new Error('Choose a folder containing model.bin, config.json and tokenizer.json. No model was downloaded.');
      speechPath=chosen.filePaths[0];await saveConfig();
      speechRestartRequired=await healthy();
      return {name:path.basename(speechPath),restartRequired:speechRestartRequired};
    };
    register('setup:speech-folder',chooseSpeech);
    register('app:choose-speech',chooseSpeech,true);
    register('app:speech-guide',()=>shell.openExternal('https://huggingface.co/Systran/faster-whisper-small.en/tree/main'),true);
    register('app:open-setup',showSetup,true);
    ipcMain.handle('app:appearance',async(event,value)=>{
      authorize(event,true);
      if(typeof value!=='string'||!Object.hasOwn(palettes,value))throw new Error('Unknown theme.');
      appearance=value;await saveConfig();
      for(const target of [window,setupWindow])if(target&&!target.isDestroyed())target.setTitleBarOverlay({color:palettes[value][0],symbolColor:palettes[value][1]});
    });

    // Show progress before starting bundled services or verifying their files.
    autoStarting=libraryChosen;
    await setup();window.show();
    try {
      if(!libraryChosen&&await nativeAvailable())return;
      if(libraryChosen)await startServices();
      if(await bridgeReady()) await window.loadURL(ORIGIN);
      else if(await healthy()&&bridgeConfig){await startServices(true);if(await bridgeReady())await window.loadURL(ORIGIN);else await setup();}
      else await setup();
    }
    catch {message='Could not open the local workspace. Check Docker Desktop and retry.';await setup();}
    autoStarting=false;
    window.show();
  });
}
app.on('before-quit', event => {
  quitting=true;
  if(shutdownComplete)return;
  event.preventDefault();
  if(shutdownStarted)return;
  shutdownStarted=true;
  void (async()=>{try{await nativeRuntime?.stop();await providerBridge?.close();}finally{shutdownComplete=true;app.quit();}})();
});
