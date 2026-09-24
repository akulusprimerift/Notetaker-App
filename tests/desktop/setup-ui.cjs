const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
 const page=await browser.newPage({viewport:{width:960,height:900}});
 await page.addInitScript(()=>{
  window.mockStatus={appearance:'blue',autoStarting:true,starting:true,message:'Preparing your saved library…',dataPath:'Synthetic profile',serviceMode:'native',nativeAvailable:true};
  window.desktopSetup={status:async()=>window.mockStatus,models:async()=>({ollamaAvailable:false,ollama:[],ollamaManifests:[],speech:null,otherFiles:[]})};
  window.desktopApp={openSpeechGuide:async()=>{window.guideOpened=true;}};
 });
 await page.goto(pathToFileURL(path.resolve('apps/desktop/setup.html')).href);
 await page.locator('#loading').waitFor();assert.equal(await page.locator('#setup-content').isVisible(),false);
 await page.screenshot({path:'.local/startup-loading.png'});
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('.loading-orb').evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.evaluate(()=>{window.mockStatus.autoStarting=false;window.mockStatus.starting=false;window.mockStatus.message='Could not start. Retry from setup.';});
 await page.locator('#setup-content').waitFor();assert.equal(await page.locator('#loading').isVisible(),false);
 await page.getByRole('button',{name:'How to get a speech model'}).click();assert.equal(await page.evaluate(()=>window.guideOpened),true);
 for(const theme of ['light','dark','pink','blue']){
  await page.evaluate(theme=>window.mockStatus.appearance=theme,theme);
  await page.locator(`html[data-theme=${theme}]`).waitFor();
  await page.screenshot({path:`.local/setup-${theme}.png`,fullPage:true});
 }
 console.log('Setup loading, recovery, guide, four themes and reduced motion passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
