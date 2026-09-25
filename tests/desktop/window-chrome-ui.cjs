// Real React rendering with synthetic network responses; microphone use is forbidden.
const {_electron:electron}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
(async()=>{
    const path=require('node:path'),fs=require('node:fs/promises');
  const profile=path.resolve('.local/chrome-'+require('node:crypto').randomUUID());await fs.mkdir(profile,{recursive:true});
  const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
  const browser=await electron.launch({executablePath:path.resolve('node_modules/electron/dist/electron.exe'),args:[path.resolve('tests/desktop/chrome-fixture.cjs'),'--user-data-dir='+profile],env});
  try{
    const page=await browser.firstWindow(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{window.desktopApp={appearance:async()=>{},openSetup:async()=>{}};localStorage.setItem('notetaker:theme','dark');navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    const lecture={id:'lecture',course_id:'course',title:'Synthetic live lecture',status:'recording',created_at:'2026-09-22T12:00:00Z'};
    const transcript={speech_model:{state:'missing',name:null},status:'queued',counts:{due:1,running:0,completed:0,failed:0},errors:['model_unavailable'],preview:'',waiting_for_audio:false,processing_delay_seconds:8,snapshot:null};
    const notes={status:'waiting_for_transcript',editing:{selected:null},preference:null,revision:null,processing:{},profile:{depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''}};
    notes.revision={id:'revision',revision:1,created_at:lecture.created_at,profile:notes.profile,metadata:{model:'synthetic'},source_issues:[],content:{issues:[],coverage:[],blocks:Array.from({length:12},(_,i)=>({id:`b${i}`,kind:i===4?'code':'explanation',topic:`Topic ${i+1}`,passages:[{id:`p${i}`,evidence_kind:'lecture_paraphrase',text:`START ${i} `+('Detailed explanation with exact preserved evidence. '.repeat(i===3?180:20))+` END ${i}`,sources:[{source_id:'source',quote:'Evidence',occurrence:0}]}]}))}};
    notes.editing={version:0,selected:null,proposal:null,proposal_valid:false,sources_changed:false};notes.status='ready';
    let socket,deletionCalls=0;
    await page.routeWebSocket('**/updates*',value=>{socket=value;});
    await page.route('**/api/**',async route=>{
      const path=new URL(route.request().url()).pathname;let body=[];
      if(path==='/api/session/open')body={owner_id:'synthetic-live',csrf_token:'test',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Synthetic course',code:'TEST',created_at:lecture.created_at}];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Synthetic course',settings:{},update_cursor:0,transcript,notes};
      else if(path.endsWith('/lectures'))body=[lecture];
      else if(path.endsWith('/finalization'))body={cursor:7,edit_version:0,audio_removed:false,status:'recording',history:[]};
      else if(path.endsWith('/deletion')){assert.equal(route.request().postDataJSON().kind,'lecture');assert.equal(route.request().postDataJSON().expected_cursor,7);deletionCalls++;body={id:'removal'};}
      else if(path.endsWith('/sources/source'))body={id:'source',text:'Synthetic evidence',source_kind:'material',label:'Synthetic source'};
      else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:1,runs:[]};
      else if(path.endsWith('/notes'))body=notes;
      else if(path.endsWith('/study/learning'))body={revision_id:null,cards:[],omitted:0,issues:[]};
      else if(path.endsWith('/study/questions'))body={revision_id:null,blocks:[],preference_id:null,model:null,enabled:false,cloud:false,sets:[]};
      else if(path.endsWith('/provider-connections'))body={connections:[]};
      else if(path.endsWith('/terminology'))body={version:0,terms:[]};
      else if(path.endsWith('/note-models'))body={models:[],available:true};
      else if(path.endsWith('/notes/stream'))return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify({active:true,text:'A streamed study explanation.'})+'\n\n'});
      await route.fulfill({json:body});
    });
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3017')+'/#lecture/lecture/notes');
    await page.locator('.note-reader').waitFor();
    assert.equal(await page.evaluate(()=>navigator.windowControlsOverlay.visible),true);
    assert.equal(await page.evaluate('typeof require'),'undefined');
    assert.equal(await page.locator('.topbar').evaluate(el=>getComputedStyle(el).webkitAppRegion),'drag');
    assert.equal(await page.locator('.sidebar-toggle').evaluate(el=>getComputedStyle(el).webkitAppRegion),'no-drag');
    assert.equal(await page.locator('.topbar').evaluate(el=>el.getBoundingClientRect().top),0);
    assert.equal(await page.locator('.sidebar').evaluate(el=>el.getBoundingClientRect().top),0);
    assert.equal(await page.locator('.desktop-titlebar').isVisible(),false);
    const rect=await page.evaluate(()=>{const r=navigator.windowControlsOverlay.getTitlebarAreaRect();return {x:r.x,width:r.width};});
    assert.ok(await page.locator('.topbar-actions').evaluate((el,rect)=>el.getBoundingClientRect().right<=rect.x+rect.width,rect));
    await page.locator('.capture-panel').evaluate(el=>el.dataset.retained='yes');
    await page.getByRole('button',{name:'Hide library',exact:true}).click();
    await page.locator('.sidebar').waitFor({state:'hidden'});
    assert.equal(await page.locator('.sidebar').evaluate(el=>el.inert),true);
    await page.getByRole('button',{name:'Show library',exact:true}).click();
    await page.locator('.sidebar').waitFor({state:'visible'});
    assert.equal(await page.locator('.capture-panel').getAttribute('data-retained'),'yes');
    await page.screenshot({path:'.local/integrated-chrome.png'});
    assert.deepEqual(errors,[]);
    console.log('Actual Electron overlay, top alignment, reserved controls, drag/no-drag and retained recorder passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});