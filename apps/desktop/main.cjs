'use strict';
const {app, BrowserWindow, Menu, dialog, ipcMain, session} = require('electron');
const path = require('node:path');
const fs = require('node:fs/promises');
const {spawn} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {ORIGIN, localPage, audioPermission} = require('./policy.cjs');
const {discoverModels} = require('./models.cjs');

app.setName('Notetaker');
const explicitData = app.commandLine.getSwitchValue('user-data-dir');
if (explicitData && path.isAbsolute(explicitData)) app.setPath('userData', explicitData);
app.enableSandbox();
let window, setupWindow, quitting = false, starting = false, message = 'Checking local services…', speechPath = '', serviceRoot = '';
const setupURL = pathToFileURL(path.join(__dirname, 'setup.html')).href;
const runtime = () => app.isPackaged ? path.join(app.getPath('userData'), 'services') : path.resolve(__dirname, '../..');
const configPath = () => path.join(app.getPath('userData'), 'desktop-settings.json');
async function saveConfig() {await fs.writeFile(configPath(),JSON.stringify({speechPath,serviceRoot}));}

async function healthy() {
  try {
    const response = await fetch(ORIGIN + '/api/health', {signal:AbortSignal.timeout(2500), redirect:'error'});
    return response.ok && (await response.json()).status === 'ok';
  } catch { return false; }
}
async function setup() {
  await window.loadURL(setupURL);
}
async function showSetup() {
  if (window.webContents.getURL() === setupURL) {window.show();return;}
  if (setupWindow && !setupWindow.isDestroyed()) {setupWindow.show();return;}
  setupWindow = new BrowserWindow({width:960,height:850,title:'Notetaker setup',
    webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true}});
  setupWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  setupWindow.webContents.on('will-navigate',(event,url)=>{if(url!==setupURL)event.preventDefault();});
  await setupWindow.loadURL(setupURL);
}
async function startServices() {
  if (starting) return;
  if (await healthy()) {message='Your local workspace is ready.';return;}
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
    const child = spawn('pwsh.exe', args, {cwd:runtime(), windowsHide:true,
      env:{...process.env, ...(app.isPackaged ? {COMPOSE_PROJECT_NAME:serviceRoot?'notetaker':'notetaker-desktop'} : {})}, stdio:['ignore','pipe','pipe']});
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

function authorize(event) {
  if (![window, setupWindow].some(w => w && !w.isDestroyed() && event.sender === w.webContents && event.senderFrame === w.webContents.mainFrame) || event.senderFrame.url !== setupURL)
    throw new Error('This action is available only in Windows setup.');
}
function register(name, action) {ipcMain.handle(name, async (event) => {authorize(event);return action();});}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => {if(window){window.show();window.focus();}});
  app.whenReady().then(async () => {
    try {const config=JSON.parse(await fs.readFile(configPath(),'utf8'));speechPath=config.speechPath || '';serviceRoot=config.serviceRoot || '';} catch { /* First launch. */ }
    if (!speechPath && !app.isPackaged) speechPath=path.join(runtime(),'.local/models/faster-whisper-small.en');
    window = new BrowserWindow({width:1360,height:950,minWidth:760,minHeight:600,title:'Notetaker',show:false,icon:path.join(__dirname,'icon.ico'),
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
        message:'Finish and save your recording before quitting.',detail:'Hide keeps recording and this workspace running. Quit closes the recorder; already journaled audio remains recoverable. Local services continue processing.'})
        .then(result => {if(result.response===1)window.hide();if(result.response===2){quitting=true;app.quit();}});
    });
    Menu.setApplicationMenu(Menu.buildFromTemplate([
      {label:'Notetaker',submenu:[{label:'Workspace',click:async()=>{window.show();if(window.webContents.getURL()===setupURL && await healthy())await window.loadURL(ORIGIN);}},
        {label:'Setup and local models',click:()=>void showSetup()}, {type:'separator'}, {label:'Quit',click:()=>window.close()}]},
      {label:'Edit',submenu:[{role:'undo'},{role:'redo'},{type:'separator'},{role:'cut'},{role:'copy'},{role:'paste'},{role:'selectAll'}]},
      {label:'View',submenu:[{role:'resetZoom'},{role:'zoomIn'},{role:'zoomOut'},{role:'togglefullscreen'}]}
    ]));
    register('setup:status',async()=>({starting,message:starting?message:await healthy()?'Your local workspace is ready.':message.startsWith('Could not')?message:'Local workspace unavailable. Start Docker Desktop and the local services.',dataPath:app.getPath('userData'),serviceRoot}));
    register('setup:start',startServices);
    register('setup:open',async()=>{if(!(await healthy()))throw new Error('Start local services first.');if(window.webContents.getURL()===setupURL)await window.loadURL(ORIGIN);window.show();if(setupWindow&&!setupWindow.isDestroyed())setupWindow.close();});
    register('setup:models',()=>discoverModels({speechPath}));
    register('setup:workspace-folder',async()=>{
      if(starting)throw new Error('Wait for service startup to finish before changing workspace.');
      const chosen=await dialog.showOpenDialog(setupWindow || window,{properties:['openDirectory'],title:'Choose the existing Notetaker workspace folder'});
      if(chosen.canceled)return;
      const folder=chosen.filePaths[0];
      for(const item of ['compose.yaml','.local/services.env','.local/s3.json']){
        try {await fs.access(path.join(folder,item));} catch {throw new Error('Choose the original workspace folder containing compose.yaml and its existing .local service configuration.');}
      }
      serviceRoot=folder;
      if(!speechPath)speechPath=path.join(folder,'.local/models/faster-whisper-small.en');
      await saveConfig();
    });
    register('setup:speech-folder',async()=>{
      const chosen=await dialog.showOpenDialog(window,{properties:['openDirectory'],title:'Choose an existing faster-whisper model folder'});
      if(chosen.canceled)return;
      const found=await discoverModels({speechPath:chosen.filePaths[0]});
      if(!found.speech)throw new Error('Choose a folder containing model.bin and config.json. No model was downloaded.');
      speechPath=chosen.filePaths[0];await saveConfig();
    });
    try {if(await healthy())await window.loadURL(ORIGIN);else await setup();}
    catch {message='Could not open the local workspace. Check Docker Desktop and retry.';await setup();}
    window.show();
  });
}
