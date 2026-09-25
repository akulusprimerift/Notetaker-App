// Real React rendering with synthetic network responses; microphone use is forbidden.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
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
    await page.setViewportSize({width:1440,height:1000});
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3017')+'/#lecture/lecture/notes');
    const reader=page.locator('.note-reader'),panel=page.locator('.note-pages-viewport');
    await reader.waitFor();
    await page.waitForFunction(()=>document.querySelectorAll('.note-page-numbers button').length>5);
    const original=await page.locator('.note-pages-flow').textContent();
    const height=await panel.evaluate(el=>el.clientHeight);
    assert.ok(height>=320&&height<=640);
    assert.equal(await panel.evaluate(el=>el.scrollHeight<=el.clientHeight+2),true,'no vertical overflow');
    await page.getByRole('button',{name:'Note section 2',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[aria-current=page]')?.textContent==='2');
    await panel.focus();await page.keyboard.press('End');
    await page.waitForFunction(()=>{const p=document.querySelector('.note-pages-viewport');return Math.abs(p.scrollWidth-p.clientWidth-p.scrollLeft)<2;});
    assert.ok(await page.getByRole('button',{name:'Next note section'}).isDisabled());
    // A source at the end remains reachable after column fragmentation.
    await page.locator('.note-pages-flow .citation-list button').last().click();
    await page.getByRole('region',{name:'Note source'}).waitFor();
    await page.getByRole('button',{name:'Close source',exact:true}).click();
    for(const width of [400,1440]){
      await page.setViewportSize({width,height:900});
      await page.waitForTimeout(400);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'fits screen');
      assert.equal(await page.locator('.note-pages-flow').textContent(),original,'all text preserved after resizing');
      assert.equal(await panel.evaluate(el=>el.scrollHeight<=el.clientHeight+2),true,'long passage stays bounded');
    }
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.getByRole('button',{name:'Note section 1',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.note-pages-viewport').scrollLeft===0);
    await page.getByLabel('App theme').selectOption('dark');
    await reader.scrollIntoViewIfNeeded();
    await page.screenshot({path:'.local/note-pages.png'});
    assert.deepEqual(errors,[]);
    console.log('Paged notes: bounded long content, numbering, keyboard, source links, resize, text preservation and reduced motion passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});