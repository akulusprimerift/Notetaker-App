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
      else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:1,runs:[]};
      else if(path.endsWith('/notes'))body=notes;
      else if(path.endsWith('/note-models'))body={models:[],available:true};
      else if(path.endsWith('/notes/stream'))return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify({active:true,text:'A streamed study explanation.'})+'\n\n'});
      await route.fulfill({json:body});
    });
    await page.setViewportSize({width:1440,height:1000});
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3016')+'/#lecture/lecture/notes');
    await page.locator('.streaming-text').waitFor();
    await page.locator('.capture-panel').evaluate(el=>el.dataset.retained='yes');
    const {mkdir}=require('node:fs/promises');
    await mkdir('.local/appearance-review',{recursive:true});
    for(const theme of ['pink','blue','dark','light']){
      await page.getByLabel('App theme').selectOption(theme);
      assert.equal(await page.locator('html').getAttribute('data-theme'),theme);
      await page.reload();
      await page.locator(`html[data-theme=${theme}]`).waitFor();
      await page.locator('.streaming-text').waitFor();
      await page.evaluate(()=>document.fonts.ready);
      await page.evaluate(()=>Promise.all(document.getAnimations().map(animation=>animation.finished.catch(()=>{}))));
      assert.match(await page.locator('.streaming-text').evaluate(el=>getComputedStyle(el).fontFamily),/^system-ui/);
      assert.match(await page.locator('h1').evaluate(el=>getComputedStyle(el).fontFamily),/Workspace Sans/);
      await page.screenshot({path:`.local/appearance-review/${theme}.png`,fullPage:true});
      await page.setViewportSize({width:400,height:850});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`${theme} fits narrow screen`);
      await page.screenshot({path:`.local/appearance-review/${theme}-narrow.png`,fullPage:true});
      await page.setViewportSize({width:1440,height:1000});
    }
    // Inspect actual font use, rather than only the declared CSS family.
    const cdp=await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');await cdp.send('CSS.enable');
    const {root}=await cdp.send('DOM.getDocument');
    const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:root.nodeId,selector:'h1'});
    const {fonts}=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
    assert.ok(fonts.some(font=>/TikTok/i.test(font.familyName)),JSON.stringify(fonts));
    await page.locator('.capture-panel').evaluate(el=>el.dataset.retained='yes');
    await page.evaluate(()=>{window.slides=[];const animate=Element.prototype.animate;Element.prototype.animate=function(frames,options){if(this.classList.contains('lecture-panel'))window.slides.push({frames,options});return animate.call(this,frames,options);};});
    await page.getByRole('tab',{name:/Transcript/}).click();
    await page.locator('.transcript-panel').waitFor();
    assert.equal(await page.evaluate(()=>window.slides.at(-1).frames[0].transform),'translateX(36px)');
    await page.waitForFunction(()=>{
      const tab=document.querySelector('.lecture-tabs [aria-selected="true"]').getBoundingClientRect();
      const marker=document.querySelector('.tab-highlight').getBoundingClientRect();
      return Math.abs(tab.x-marker.x)<1&&Math.abs(tab.width-marker.width)<1;
    });
    await page.getByRole('tab',{name:/Study notes/}).click();
    await page.locator('.streaming-text').waitFor();
    assert.equal(await page.evaluate(()=>window.slides.at(-1).frames[0].transform),'translateX(-36px)');
    await page.emulateMedia({reducedMotion:'reduce'});
    const count=await page.evaluate(()=>window.slides.length);
    await page.getByRole('tab',{name:/Transcript/}).click();
    await page.locator('.transcript-panel').waitFor();
    assert.equal(await page.evaluate(()=>window.slides.length),count);
    assert.equal(await page.locator('.capture-panel').getAttribute('data-retained'),'yes');
    await page.evaluate(()=>{location.hash='';});
    await page.locator('.course-card').waitFor();
    assert.equal(await page.locator('.course-card').evaluate(el=>getComputedStyle(el).backdropFilter.includes('blur')),true);
    for(const theme of ['pink','blue','dark']){
      await page.getByLabel('App theme').selectOption(theme);
      await page.evaluate(()=>Promise.all(document.getAnimations().map(animation=>animation.finished.catch(()=>{}))));
      await page.screenshot({path:`.local/appearance-review/${theme}-dashboard.png`,fullPage:true});
    }
    assert.deepEqual(errors,[]);
    console.log('Four persisted themes, local geometric font rendering, preserved reading font, 400px layouts, directional slide, reduced motion and retained recorder passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
