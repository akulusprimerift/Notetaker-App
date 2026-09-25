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
 assert.equal(await page.getByRole('progressbar',{name:'Starting library'}).getAttribute('aria-valuenow'),null);
 assert.match(await page.locator('.liquid-progress>span').evaluate(el=>getComputedStyle(el).animationName),/liquid-travel/);
 await page.waitForTimeout(700);
 await page.screenshot({path:'.local/startup-loading.png'});
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('.loading-orb').evaluate(el=>getComputedStyle(el).animationName),'none');
 assert.equal(await page.locator('.liquid-progress>span').evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.evaluate(()=>{window.mockStatus.autoStarting=false;window.mockStatus.starting=false;window.mockStatus.message='Could not start. Retry from setup.';});
 await page.locator('#setup-content').waitFor();assert.equal(await page.locator('#loading').isVisible(),false);
 await page.getByRole('button',{name:'How to get a speech model'}).click();assert.equal(await page.evaluate(()=>window.guideOpened),true);
 for(const theme of ['light','dark','pink','blue']){
  await page.evaluate(theme=>window.mockStatus.appearance=theme,theme);
  await page.locator(`html[data-theme=${theme}]`).waitFor();
  const contrast=await page.locator('#native').evaluate(el=>{
    const luminance=color=>{const values=color.match(/[\d.]+/g).slice(0,3).map(Number).map(value=>{value/=255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;});return values[0]*.2126+values[1]*.7152+values[2]*.0722;};
    const style=getComputedStyle(el),a=luminance(style.color),b=luminance(style.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
  });assert.ok(contrast>=4.5,theme+' setup primary contrast '+contrast);
  await page.screenshot({path:`.local/setup-${theme}.png`,fullPage:true});
 }
 console.log('Setup loading, recovery, guide, four themes and reduced motion passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
