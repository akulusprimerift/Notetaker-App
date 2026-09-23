const path=require('node:path');const fs=require('node:fs/promises');const assert=require('node:assert/strict');const {randomUUID}=require('node:crypto');
const {_electron:electron}=require('../../.venv/Lib/site-packages/playwright/driver/package');
(async()=>{
const root=path.resolve(__dirname,'../..'),executablePath=path.resolve(process.argv[2]),model=path.resolve(process.argv[3]);
const profile=path.join(root,'.local','speech-setup-smoke-'+randomUUID());await fs.mkdir(profile,{recursive:true});
let application;
async function launch(){const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;application=await electron.launch({executablePath,args:['--user-data-dir='+profile],env,timeout:240000});return application.firstWindow();}
async function quit(){const stopped=application.waitForEvent('close',{timeout:60000});await application.evaluate(({app})=>app.quit()).catch(()=>{});await stopped;application=null;}
try{
let page=await launch();await page.locator('#native').click();await page.locator('#status').filter({hasText:'Audio saving is ready.'}).waitFor({timeout:660000});await page.locator('#open').click();await page.waitForURL('http://127.0.0.1:3000/');
// A string avoids Bun folding `typeof require` in the test runner itself.
assert.equal(await page.evaluate('typeof require'),'undefined');
const lecture=await page.evaluate(async()=>{
navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};
const session=await (await fetch('/api/session/open',{method:'POST'})).json();
async function post(url,body){const r=await fetch('/api'+url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token,'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(body)});if(!r.ok)throw new Error('Synthetic setup failed');return r.json();}
const course=await post('/courses',{name:'Synthetic speech setup',code:'TEST'});return post('/courses/'+course.id+'/lectures',{title:'Synthetic readiness check'});
});
await page.goto('http://127.0.0.1:3000/#lecture/'+lecture.id);
await page.getByText('No usable speech model selected',{exact:true}).waitFor();
await application.evaluate(({dialog},folder)=>{dialog.showMessageBox=async()=>({response:1});dialog.showOpenDialog=async()=>({canceled:false,filePaths:[folder]});},model);
await page.getByRole('button',{name:'Select speech model',exact:true}).click();
await page.getByText(/selected. Finish recording and wait for confirmed saves/).waitFor({timeout:60000});
const config=JSON.parse(await fs.readFile(path.join(profile,'desktop-settings.json'),'utf8'));
assert.equal(config.speechPath,model);
await quit();page=await launch();await page.waitForURL('http://127.0.0.1:3000/',{timeout:660000});await page.goto('http://127.0.0.1:3000/#lecture/'+lecture.id);
await page.locator('.speech-model > .section-row strong').filter({hasText:'Speech model active · ready to transcribe'}).waitFor({timeout:180000});
assert.equal(await page.getByRole('button',{name:'★ Mark Important'}).count(),0);
await page.getByRole('region',{name:'Live transcript preview'}).waitFor();
await page.getByRole('button',{name:'How to get a model'}).click();await page.getByRole('dialog',{name:'Set up speech recognition'}).waitFor();await page.keyboard.press('Escape');
console.log(JSON.stringify({packaged_setup:'passed',selection_and_restart:'passed',worker_ready:'passed',renderer_isolated:true,microphone:false,profile}));
}finally{if(application)await quit();}
})().catch(error=>{console.error(error);process.exitCode=1});
