// Real Chromium AudioWorklet/worker/IndexedDB; generated tone and simulated API only.
const http=require('node:http');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
(async()=>{
  const root=path.resolve(__dirname,'../../apps/web/public/capture');
  const server=http.createServer(async(req,res)=>{
    if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end('<!doctype html><title>Synthetic power capture check</title>');return;}
    if(!/^\/capture\/[a-z-]+\.(mjs|js)$/.test(req.url)){res.writeHead(404);res.end();return;}
    try{res.setHeader('Content-Type','text/javascript');res.end(await fs.readFile(path.join(root,path.basename(req.url))));}
    catch{res.writeHead(404);res.end();}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({headless:true,executablePath:process.env.NOTETAKER_CHROMIUM,args:['--autoplay-policy=no-user-gesture-required']});
    const page=await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.evaluate(async()=>{
      const {Recorder}=await import('/capture/recorder.mjs');
      window.powerListener=null;
      window.desktopApp={platform:'darwin',onPower:fn=>{window.powerListener=fn;return ()=>{window.powerListener=null;};}};
      // Any accidental microphone request fails the check, even with no permissions.
      navigator.mediaDevices.getUserMedia=()=>{throw Error('Physical microphone must never be requested');};
      window.offline=true;window.uploaded=[];window.sealed=null;
      const recorder=new Recorder({owner:'synthetic-owner',lecture:'synthetic-lecture',csrf:'test',onChange:state=>{window.captureState=state;},
        streamFactory:async()=>{
          const context=new AudioContext(),tone=context.createOscillator(),output=context.createMediaStreamDestination();
          tone.connect(output);tone.start();await context.resume();
          for(const track of output.stream.getTracks()){
            const stop=track.stop.bind(track);track.stop=()=>{stop();tone.stop();void context.close();};
          }
          return output.stream;
        },fetcher:async(url,init)=>{
          let result={};
          if(url.endsWith('/capture'))result={available:true,capture_epoch:0,runs:[]};
          else if(url.endsWith('/capture-runs'))result={capture_epoch:1,gaps:[]};
          else if(url.endsWith('/heartbeat')&&window.offline)throw Error('Synthetic offline');
          else if(init.method==='PUT'){
            const identity=JSON.parse(init.headers['X-Chunk-Identity']);
            const bytes=await init.body.arrayBuffer();
            const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
            if(hash!==identity.sha256)throw Error('Changed audio bytes');
            window.uploaded.push(identity);
            result={...identity,storage_state:'verified',chunk_id:'chunk-'+identity.sequence,manifest_version:1};
          }else if(url.endsWith('/manifest'))result={manifest_version:1};
          else if(url.endsWith('/seal'))window.sealed=JSON.parse(init.body);
          return new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json'}});
        }});
      window.recorder=recorder;await recorder.init();await recorder.start();
    });
    await page.waitForFunction(()=>window.captureState.active&&window.captureState.local.some(row=>row.samples>0));
    await page.evaluate(()=>window.powerListener('suspend'));
    await page.waitForFunction(()=>!window.captureState.active&&!window.captureState.working);
    const interrupted=await page.evaluate(()=>window.recorder.journal.get('synthetic-owner',window.recorder.run.id));
    assert.ok(interrupted.samples>0);assert.ok(interrupted.pending_bytes>0);
    assert.equal(interrupted.stopped,true);assert.equal(interrupted.server_sealed,false);
    assert.equal(interrupted.gaps[0].reason,'sleep_or_suspension');
    await page.evaluate(async()=>{window.powerListener('resume');window.offline=false;await window.recorder.sync();});
    const saved=await page.evaluate(()=>({state:window.captureState,seal:window.sealed,uploaded:window.uploaded}));
    assert.equal(saved.state.active,false);assert.equal(saved.seal.final_sample_count,interrupted.samples);
    assert.deepEqual(saved.seal.gaps,interrupted.gaps);assert.match(saved.state.message,/missing time was not recorded/);
    assert.equal(saved.uploaded.reduce((n,row)=>n+row.sample_count,0),interrupted.samples);
    // A 48 kHz device stream is resampled to the 16 kHz speech rate before packaging.
    assert.ok(saved.uploaded.every(row=>row.sample_rate===16000&&row.byte_length===44+row.sample_count*2));
    // Reuse the very same recorder after Stop, without navigation or reload.
    for(let cycle=0;cycle<3;cycle++){
      const priorId=await page.evaluate(()=>window.recorder.run.id);
      await page.evaluate(()=>window.recorder.start());
      await page.waitForFunction(()=>window.captureState.active&&window.recorder.run.samples>0);
      assert.notEqual(await page.evaluate(()=>window.recorder.run.id),priorId);
      await page.evaluate(()=>window.recorder.stop());
      const stopped=await page.evaluate(()=>({run:window.recorder.run,state:window.captureState,seal:window.sealed}));
      assert.equal(stopped.state.working,false);assert.equal(stopped.state.active,false);
      assert.equal(stopped.run.server_sealed,true);assert.equal(stopped.run.pending_bytes,0);
      assert.equal(stopped.seal.final_sample_count,stopped.run.samples);
    }
    await page.evaluate(async()=>{
      const {openJournal}=await import('/capture/journal.mjs');
      const id=window.recorder.run.id;await window.recorder.dispose();
      const journal=await openJournal();window.reopened=await journal.get('synthetic-owner',id);journal.close();
    });
    const reopened=await page.evaluate(()=>window.reopened);
    assert.equal(reopened.server_sealed,true);assert.equal(reopened.pending_bytes,0);assert.deepEqual(reopened.gaps,[]);
    assert.equal(await page.evaluate(()=>window.powerListener),null);
    console.log('Synthetic Chromium sleep/offline/wake/retry, three stop/restart cycles and journal reopen passed; interrupted samples:',interrupted.samples);
  }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
