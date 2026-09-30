// Fresh setup only: never open a student library or request a microphone.
const path=require('node:path');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const {randomUUID}=require('node:crypto');
const {_electron:electron}=require('../../.venv/Lib/site-packages/playwright/driver/package');
(async()=>{
  const root=path.resolve(__dirname,'../..');
  const profile=path.join(root,'.local','foundation-smoke-'+randomUUID());
  const bundle=path.join(profile,'synthetic-runtime');
  await fs.mkdir(bundle,{recursive:true});
  // Only advertise first-launch availability; no synthetic executable is run.
  await fs.writeFile(path.join(bundle,'runtime-manifest.json'),'{}');
  const env={...process.env,NOTETAKER_NATIVE_RESOURCES:bundle};delete env.ELECTRON_RUN_AS_NODE;
  const app=await electron.launch({executablePath:path.join(root,'node_modules/electron/dist/electron.exe'),
    args:[root,'--user-data-dir='+profile],env});
  try{
    const page=await app.firstWindow();
    await page.waitForURL(/setup\.html$/);
    await page.locator('#native').waitFor({state:'visible'});
    assert.equal(await page.evaluate('typeof require'),'undefined');
    const prefs=await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences());
    assert.equal(prefs.sandbox,true);assert.equal(prefs.contextIsolation,true);assert.equal(prefs.nodeIntegration,false);
    assert.equal(await page.evaluate(()=>window.desktopApp.platform),'win32');
    await page.evaluate(()=>{
      window.syntheticPower=[];
      window.unsubscribePower=window.desktopApp.onPower(kind=>window.syntheticPower.push(kind));
    });
    await app.evaluate(({BrowserWindow})=>{
      const contents=BrowserWindow.getAllWindows()[0].webContents;
      contents.send('app:power','suspend');contents.send('app:power','unrecognized');contents.send('app:power','resume');
    });
    await page.waitForFunction(()=>window.syntheticPower.length===2);
    assert.deepEqual(await page.evaluate(()=>window.syntheticPower),['suspend','resume']);
    await page.evaluate(()=>window.unsubscribePower());
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].webContents.send('app:power','suspend'));
    // A round-trip confirms the unsubscribe has been applied without exposing raw IPC.
    await page.evaluate(()=>window.desktopSetup.status());
    assert.deepEqual(await page.evaluate(()=>window.syntheticPower),['suspend','resume']);
    assert.equal(await fs.stat(path.join(profile,'standalone-library')).then(()=>true,()=>false),false);
    console.log('Isolated Windows Electron setup and renderer isolation passed:',profile);
  }finally{
    const closed=app.waitForEvent('close',{timeout:15000});
    await app.evaluate(({app})=>app.quit());await closed;
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
