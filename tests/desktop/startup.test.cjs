const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const {EventEmitter}=require('node:events');
async function launch(config,{failure=false}={}){
  const handlers=new Map(),windows=[],loads=[];let ready,starts=0,stored;
  class Window extends EventEmitter{
    constructor(options){super();this.options=options;this.webContents=new EventEmitter();this.webContents.mainFrame={url:''};this.webContents.getURL=()=>this.url||'';this.webContents.setWindowOpenHandler=()=>{};windows.push(this);}
    async loadURL(url){this.url=url;this.webContents.mainFrame.url=url;loads.push({url,status:url.endsWith('setup.html')&&handlers.has('setup:status')?await handlers.get('setup:status')(event(this)):null});}
    show(){} focus(){} isDestroyed(){return false;} setTitleBarOverlay(value){this.overlay=value;}
  }
  const event=w=>({sender:w.webContents,senderFrame:w.webContents.mainFrame});
  const app=new EventEmitter();Object.assign(app,{isPackaged:true,setName(){},setPath(){},enableSandbox(){},getPath:()=>'/test-profile',commandLine:{getSwitchValue:()=>''},requestSingleInstanceLock:()=>true,whenReady:()=>({then:fn=>{ready=fn();}})});
  const electron={app,BrowserWindow:Window,dialog:{},ipcMain:{handle:(name,fn)=>handlers.set(name,fn)},session:{defaultSession:{setPermissionCheckHandler(){},setPermissionRequestHandler(){}}},Menu:{setApplicationMenu(){}},shell:{},safeStorage:{}};
  class Runtime{async start(){starts++;if(failure)throw Error('Synthetic startup failure');this.ready=true;}async stop(){}}
  const mocks={electron,'node:fs/promises':{readFile:async()=>{if(!config)throw Error('missing');return JSON.stringify(config);},writeFile:async(_,data)=>{stored=JSON.parse(data);},rename:async()=>{},access:async()=>{}},'./policy.cjs':{ORIGIN:'http://127.0.0.1:3000',localPage:u=>u.startsWith('http://127.0.0.1:3000'),audioPermission:()=>false},'./models.cjs':{},'./powershell.cjs':{},'./provider-bridge.cjs':{ProviderBridge:class{async start(){return {port:1};}}},'./native-runtime.cjs':{NativeRuntime:Runtime}};
  vm.runInNewContext(fs.readFileSync('apps/desktop/main.cjs','utf8'),{require:name=>mocks[name]||require(name),__dirname:path.resolve('apps/desktop'),process:{resourcesPath:'/resources',env:{}},console,fetch:async()=>({ok:true,json:async()=>({status:'ok',provider_bridge_port:1})}),AbortSignal});
  await ready;return {starts,loads,windows,handlers,event,stored:()=>stored};
}
test('returning native library shows loading then opens workspace automatically',async()=>{
  const result=await launch({serviceMode:'native',libraryChosen:true,appearance:'blue'});
  assert.equal(result.starts,1);assert.equal(result.loads[0].status.autoStarting,true);
  assert.equal(result.loads.at(-1).url,'http://127.0.0.1:3000');
  assert.equal(result.windows[0].options.titleBarOverlay.color,'#00000000');
  assert.equal(result.windows[0].options.webPreferences.sandbox,true);
});
test('fresh install keeps explicit library selection and failed startup returns recovery controls',async()=>{
  const fresh=await launch(null);assert.equal(fresh.starts,0);assert.equal(fresh.loads[0].status.autoStarting,false);
  const failed=await launch({serviceMode:'native',libraryChosen:true},{failure:true});
  const status=await failed.handlers.get('setup:status')(failed.event(failed.windows[0]));
  assert.equal(status.autoStarting,false);assert.match(status.message,/Could not start/);assert.match(failed.loads.at(-1).url,/setup.html$/);
});
test('appearance IPC persists an allowlisted theme and rejects foreign frames',async()=>{
  const result=await launch({serviceMode:'native',libraryChosen:true});const change=result.handlers.get('app:appearance');
  await change(result.event(result.windows[0]),'pink');assert.equal(result.stored().appearance,'pink');assert.equal(result.windows[0].overlay.color,'#00000000');assert.equal(result.windows[0].overlay.symbolColor,'#4b1830');
  await assert.rejects(()=>change(result.event(result.windows[0]),'unknown'));
  await assert.rejects(()=>change(result.event(result.windows[0]),['light']));
  await assert.rejects(()=>change({sender:{},senderFrame:{url:'http://127.0.0.1:3000'}},'dark'));
});
