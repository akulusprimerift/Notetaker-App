// Run against the local workspace; no microphone requests and no student edits.
const path = require('node:path');
const fs = require('node:fs/promises');
const assert = require('node:assert/strict');
const {_electron:electron} = require('../../.venv/Lib/site-packages/playwright/driver/package');

(async()=>{
  const root=path.resolve(__dirname,'../..');
  const data=path.join(root,'.local','desktop-smoke-profile');await fs.mkdir(data,{recursive:true});
  const environment={...process.env};delete environment.ELECTRON_RUN_AS_NODE;
  const application=await electron.launch({executablePath:process.env.NOTETAKER_TEST_EXECUTABLE || path.join(root,'node_modules/electron/dist/electron.exe'),
    args:[...(process.env.NOTETAKER_TEST_EXECUTABLE ? [] : [root]),'--user-data-dir='+data],env:environment});
  try{
    const page=await application.firstWindow();
    await page.waitForLoadState('domcontentloaded');
    assert.equal(await page.evaluate(()=>typeof require),'undefined');
    const prefs=await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences());
    assert.equal(prefs.sandbox,true);assert.equal(prefs.contextIsolation,true);assert.equal(prefs.nodeIntegration,false);
    if(page.url().startsWith('http://127.0.0.1:3000')){
      await page.getByRole('heading',{name:'Your lecture library.'}).waitFor();
      const denied=await page.evaluate(async()=>{try{await window.desktopSetup.models();return false;}catch{return true;}});
      assert.equal(denied,true);
      const opening=application.waitForEvent('window');
      await application.evaluate(({Menu})=>Menu.getApplicationMenu().items[0].submenu.items[1].click());
      await opening;
      const setup=application.windows().find(p=>p!==page);
      await setup.getByRole('heading',{name:'Models on this computer'}).waitFor();
      await application.evaluate(()=>{globalThis.smokeFetch=globalThis.fetch;globalThis.fetch=async()=>{throw new Error('synthetic offline');};});
      const offline=await setup.evaluate(()=>window.desktopSetup.status());
      assert.match(offline.message,/unavailable/i);
      await application.evaluate(()=>{globalThis.fetch=globalThis.smokeFetch;delete globalThis.smokeFetch;});
      await application.evaluate(({dialog},folder)=>{globalThis.smokeDialog=dialog.showOpenDialog;dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},root);
      await setup.getByRole('button',{name:'Use existing workspace folder'}).click();
      await setup.locator('#location').filter({hasText:'Existing workspace:'}).waitFor();
      await application.evaluate(({dialog})=>{dialog.showOpenDialog=globalThis.smokeDialog;delete globalThis.smokeDialog;});
      await setup.getByRole('button',{name:'Refresh model discovery'}).click();
      await setup.locator('#models').filter({hasText:'Ollama'}).waitFor();
      await setup.screenshot({path:path.join(root,'.local/desktop-setup.png'),fullPage:true});
      assert.ok(page.url().startsWith('http://127.0.0.1:3000'));
      await setup.close();
      // Exercise the actual production journal module with isolated synthetic records.
      const recovered=await page.evaluate(async()=>{
        const {openJournal}=await import('/capture/journal.mjs');
        const {encodeWav}=await import('/capture/pcm.mjs');
        const name='desktop-test-'+crypto.randomUUID(),owner='desktop-test',id=crypto.randomUUID();
        let journal=await openJournal(name);
        try{
          await journal.put({id,owner_id:owner,lecture_id:'synthetic',capture_epoch:1,sample_rate:48000,next_sequence:0,samples:0,pending_bytes:0,stopped:false});
          await journal.append(owner,id,encodeWav(new Float32Array([0,.5,-.5]),48000),'a'.repeat(64),3);
          journal.close();journal=await openJournal(name);
          const preserved=(await journal.get(owner,id)).samples===3 && (await journal.pending(owner,id)).length===1;
          await journal.purge(owner,id);return preserved;
        }finally{journal.close();indexedDB.deleteDatabase(name);}
      });
      assert.equal(recovered,true);
      await page.screenshot({path:path.join(root,'.local/desktop-workspace.png'),fullPage:true});
    }else{
      await page.getByRole('heading',{name:'Models on this computer'}).waitFor();
      await page.screenshot({path:path.join(root,'.local/desktop-setup.png'),fullPage:true});
    }
    await application.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.hide();w.show();});
    console.log('PASS: Electron isolation, setup, outage reporting, workspace reuse, local model discovery and window hide/reopen; synthetic journal checked when services are available.');
  }finally{
    await application.evaluate(({app,BrowserWindow})=>{for(const w of BrowserWindow.getAllWindows())w.removeAllListeners('close');app.quit();}).catch(()=>{});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
