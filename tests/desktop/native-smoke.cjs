// Isolated PostgreSQL/Seaweed library, synthetic PCM only; no microphone or providers.
const path=require('node:path');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const {randomUUID}=require('node:crypto');
const {_electron:electron}=require('../../.venv/Lib/site-packages/playwright/driver/package');

(async()=>{
  const root=path.resolve(__dirname,'../..');
  const resources=path.resolve(process.argv[2]||'');
  assert.ok(process.argv[2],'Pass the prepared native runtime.');
  const profile=path.join(root,'.local','standalone-smoke-'+randomUUID());
  await fs.mkdir(profile,{recursive:true});
  const env={...process.env,NOTETAKER_NATIVE_RESOURCES:resources};delete env.ELECTRON_RUN_AS_NODE;
  const executable=process.env.NOTETAKER_TEST_EXECUTABLE||path.join(root,'node_modules/electron/dist/electron.exe');
  const args=[...(process.env.NOTETAKER_TEST_EXECUTABLE?[]:[root]),'--user-data-dir='+profile];
  let application;
  let firstLaunch=true;
  async function launch(){
    application=await electron.launch({executablePath:executable,args,env,timeout:240000});
    const page=await application.firstWindow();
    if(firstLaunch){
      await page.locator('#native').click();
      await page.locator('#status').filter({hasText:/Your local workspace is ready\.|Audio saving is ready\.|Could not/}).waitFor({timeout:660000});
      assert.doesNotMatch(await page.locator('#status').textContent(),/Could not/,'Startup failed; inspect the setup message before retrying.');
      await page.locator('#open').click();
      firstLaunch=false;
    }
    await page.waitForURL('http://127.0.0.1:3000/',{timeout:660000}).catch(async error=>{
      console.error('Setup status:',await page.locator('#status').textContent().catch(()=>''));throw error;
    });
    await page.getByRole('heading',{name:'Your lecture library.'}).waitFor();
    // Evaluate in the renderer: Bun can constant-fold typeof require in a callback.
    assert.equal(await page.evaluate('typeof require'),'undefined');
    await page.evaluate(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    return page;
  }
  async function close(){
    const app=application;application=null;
    const exited=app.waitForEvent('close',{timeout:60000});
    await app.evaluate(({app})=>app.quit()).catch(()=>{});
    await exited;
    // The host closes its own PostgreSQL tree before Electron completes quit.
    await new Promise(resolve=>setTimeout(resolve,2000));
  }
  try{
    let page=await launch();
    const chrome=await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].getContentBounds());
    assert.ok(chrome.width>0);
    assert.equal(await page.evaluate(()=>navigator.windowControlsOverlay?.visible),true);
    assert.equal(await page.locator('.topbar').evaluate(el=>getComputedStyle(el).webkitAppRegion),'drag');
    await page.getByLabel('App theme').selectOption('blue');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'blue');
    assert.equal(await page.locator('h1').evaluate(element=>getComputedStyle(element).fontFamily.includes('Workspace Sans')),true);
    await page.screenshot({path:path.join(profile,'blue-packaged.png')});
    const saved=await page.evaluate(async()=>{
      const session=await (await fetch('/api/session/open',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
      async function command(url,body,method='POST',extra={}){
        const response=await fetch('/api'+url,{method,headers:{'Content-Type':'application/json','x-csrf-token':session.csrf_token,'idempotency-key':crypto.randomUUID(),...extra},body:JSON.stringify(body)});
        if(!response.ok)throw new Error(url+': '+response.status+' '+await response.text());
        return response.json();
      }
      const course=await command('/courses',{name:'Standalone synthetic verification',code:'TEST'});
      const lecture=await command(`/courses/${course.id}/lectures`,{title:'Synthetic preserved audio'});
      const grant=crypto.randomUUID()+crypto.randomUUID();
      const run=await command(`/lectures/${lecture.id}/capture-runs`,{sample_rate:48000,grant,expected_capture_epoch:0});
      const {encodeWav}=await import('/capture/pcm.mjs');
      const data=encodeWav(new Float32Array(48000),48000);
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');
      const identity={run_id:run.id,capture_epoch:run.capture_epoch,sequence:0,start_sample:0,sample_count:48000,sample_rate:48000,channels:1,encoding:'pcm_s16le_wav',sha256:hash,byte_length:data.byteLength};
      const response=await fetch(`/api/lectures/${lecture.id}/capture-runs/${run.id}/chunks/0`,{method:'PUT',headers:{'Content-Type':'audio/wav','x-csrf-token':session.csrf_token,'x-capture-grant':grant,'x-chunk-identity':JSON.stringify(identity)},body:data});
      if(!response.ok)throw new Error('Audio save: '+response.status+' '+await response.text());
      const receipt=await response.json();
      const manifest=await(await fetch(`/api/lectures/${lecture.id}/capture-runs/${run.id}/manifest`)).json();
      await command(`/lectures/${lecture.id}/capture-runs/${run.id}/seal`,{expected_version:manifest.manifest_version,last_sequence:0,final_sample_count:48000,gaps:[]},'POST',{'x-capture-grant':grant});
      return {course:course.id,lecture:lecture.id,chunk:receipt.chunk_id,hash,storage:receipt.storage_state};
    });
    assert.equal(saved.storage,'verified');
    const exports=await page.evaluate(async lecture=>{
      const session=await(await fetch('/api/session/open',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
      const base='/api/lectures/'+lecture;
      const state=await(await fetch(base+'/finalization')).json();
      const response=await fetch(base+'/finalization',{method:'POST',headers:{'Content-Type':'application/json','x-csrf-token':session.csrf_token,'idempotency-key':crypto.randomUUID()},body:JSON.stringify({expected_cursor:state.cursor,expected_edit_version:state.edit_version,available_only:true})});
      if(!response.ok)throw Error('Synthetic finalization failed: '+await response.text());
      let snapshot;
      for(let attempt=0;attempt<40;attempt++){
        const final=await(await fetch(base+'/finalization')).json();snapshot=final.history.find(row=>row.snapshot_id)?.snapshot_id;
        if(snapshot)break;await new Promise(resolve=>setTimeout(resolve,500));
      }
      if(!snapshot)throw Error('Final snapshot did not settle');
      const files={};
      for(const format of ['docx','pptx','txt']){
        const file=await fetch(base+'/final-snapshots/'+snapshot+'/export?format='+format);
        if(!file.ok)throw Error(format+' export failed: '+await file.text());
        files[format]=Array.from(new Uint8Array(await file.arrayBuffer()));
      }
      return files;
    },saved.lecture);
    for(const [format,bytes] of Object.entries(exports)){
      if(format!=='txt')assert.equal(Buffer.from(bytes).subarray(0,2).toString(),'PK');
      await fs.writeFile(path.join(profile,'synthetic-notes.'+format),Buffer.from(bytes));
    }

    await close();
    page=await launch();
    await page.waitForFunction(()=>document.documentElement.dataset.theme==='blue');
    await page.getByLabel('App theme').selectOption('pink');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'pink');
    await page.screenshot({path:path.join(profile,'pink-packaged.png')});
    const preserved=await page.evaluate(async saved=>{
      const courses=await(await fetch('/api/courses')).json();
      const response=await fetch(`/api/lectures/${saved.lecture}/audio-chunks/${saved.chunk}`);
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await response.arrayBuffer())),v=>v.toString(16).padStart(2,'0')).join('');
      return {course:courses.some(course=>course.id===saved.course),hash,status:response.status};
    },saved);
    assert.equal(preserved.status,200);assert.equal(preserved.course,true);assert.equal(preserved.hash,saved.hash);
    console.log(JSON.stringify({standalone_launch:true,postgres_migrations:true,synthetic_audio_verified:true,
      close_reopen_readback:true,electron_isolation:true,appearance_and_theme_persistence:true,portable_snapshot_exports:true,window_controls_overlay:true,profile,limitations:'No microphone, human quality, clean-machine or long-duration qualification.'},null,2));
  }finally{if(application)await close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
