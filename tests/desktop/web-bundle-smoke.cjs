// Runs the staged bundle outside the repository; all API responses are synthetic.
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const net = require('node:net');
const {spawn} = require('node:child_process');
const {once} = require('node:events');
const assert = require('node:assert/strict');
const {chromium} = require('../../.venv/Lib/site-packages/playwright/driver/package');
const {inventory} = require('../../scripts/prepare-desktop-web.cjs');

(async()=>{
  assert.ok(process.argv[2], 'Pass a prepared web bundle folder.');
  const source = path.resolve(process.argv[2]);
  const manifest = JSON.parse(await fs.readFile(path.join(source,'bundle-manifest.json'),'utf8'));
  const actual = (await inventory(source)).filter(file=>file.path!=='bundle-manifest.json');
  assert.deepEqual(actual,manifest.files,'Staged files must match their recorded hashes.');
  const directory = await fs.mkdtemp(path.join(os.tmpdir(),'notetaker-web-smoke-'));
  let child, browser;
  try {
    await fs.cp(source,directory,{recursive:true});
    const socket = net.createServer();socket.listen(0,'127.0.0.1');await once(socket,'listening');
    const port = socket.address().port;await new Promise(resolve=>socket.close(resolve));
    child = spawn(process.execPath,[path.join(directory,manifest.entrypoint)],{
      cwd:directory,windowsHide:true,stdio:['ignore','pipe','pipe'],
      env:{SystemRoot:process.env.SystemRoot,TEMP:process.env.TEMP,TMP:process.env.TMP,
        NODE_ENV:'production',HOSTNAME:'127.0.0.1',PORT:String(port),NEXT_TELEMETRY_DISABLED:'1'},
    });
    let output='',failure;
    child.on('error',error=>{failure=error;});
    child.stdout.on('data',data=>{output=(output+data).slice(-8000);});
    child.stderr.on('data',data=>{output=(output+data).slice(-8000);});
    const origin='http://127.0.0.1:'+port;
    let ready=false;
    const deadline=Date.now()+60000;
    while(Date.now()<deadline){
      if(failure)throw failure;
      if(child.exitCode!==null)throw new Error('Staged server exited: '+output);
      try{const response=await fetch(origin,{signal:AbortSignal.timeout(1000)});ready=response.ok;}catch{/* Starting. */}
      if(ready)break;
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    assert.ok(ready,'Staged server did not become ready: '+output);
    for(const asset of ['worklet.js','worker.mjs','recorder.mjs','journal.mjs','pcm.mjs']){
      assert.equal((await fetch(origin+'/capture/'+asset)).status,200,asset);
    }
    browser=await chromium.launch({headless:true});
    const page=await browser.newPage(),errors=[],badAssets=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('response',response=>{if(response.url().includes('/_next/')&&response.status()>=400)badAssets.push(response.url());});
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    await page.route('**/api/**',route=>{
      const endpoint=new URL(route.request().url()).pathname;
      return route.fulfill({json:endpoint==='/api/session/open'?{owner_id:'synthetic',csrf_token:'test',preview:true}:[]});
    });
    await page.goto(origin);
    await page.getByRole('heading',{name:'Your lecture library.'}).waitFor();
    await page.getByRole('button',{name:'+ New course',exact:true}).click();
    await page.getByRole('textbox').first().fill('Synthetic bundle check');
    assert.deepEqual(errors,[]);assert.deepEqual(badAssets,[]);
    console.log(JSON.stringify({isolated_bundle:true,manifest_verified:true,react_hydration:true,
      capture_assets:5,api:'synthetic intercepted responses',runtime:process.version,
      limits:'No packaged Electron, real API, inference, microphone or installed workflow qualification.'},null,2));
  }finally{
    if(browser)await browser.close();
    if(child&&child.exitCode===null){const exited=once(child,'exit');child.kill();await exited;}
    assert.equal(path.dirname(path.resolve(directory)),path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('notetaker-web-smoke-'));
    await fs.rm(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
