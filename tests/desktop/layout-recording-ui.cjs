// Real React workspace with synthetic API responses and oscillator audio; no microphone.
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const playwrightDriver=process.env.NOTETAKER_PLAYWRIGHT_DRIVER||
  (process.platform==='win32'?path.resolve(__dirname,'../../.venv/Lib/site-packages/playwright/driver/package'):
    execFileSync('uv',['run','--no-project','python','-c','import pathlib, playwright; print(pathlib.Path(playwright.__file__).parent / "driver" / "package")'],
      {cwd:path.resolve(__dirname,'../..'),encoding:'utf8'}).trim());
const {chromium}=require(playwrightDriver);

(async()=>{
  const browser=await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:760}}),errors=[];
    page.on('pageerror',error=>errors.push(error.stack||error.message));
    await page.addInitScript(()=>{
      window.__syntheticMicCalls=0;
      navigator.storage.estimate=async()=>({quota:2**40,usage:0});
      navigator.storage.persist=async()=>true;
      navigator.mediaDevices.getUserMedia=async()=>{
        window.__syntheticMicCalls++;
        const context=new AudioContext(),tone=context.createOscillator(),output=context.createMediaStreamDestination();
        tone.frequency.value=440;tone.connect(output);tone.start();await context.resume();
        for(const track of output.stream.getTracks()){
          const stop=track.stop.bind(track);track.stop=()=>{stop();tone.stop();void context.close();};
        }
        return output.stream;
      };
    });
    const created='2026-10-03T12:00:00Z';
    const course={id:'course',name:'Synthetic course',code:'TEST',created_at:created};
    const lecture={id:'lecture',course_id:'course',title:'Synthetic navigation lecture',status:'prepared',audio_removed:false,created_at:created,update_cursor:0};
    const transcript={speech_model:{state:'ready',name:'synthetic'},status:'not_started',counts:{due:0,running:0,completed:0,failed:0},errors:[],preview:'',waiting_for_audio:false,processing_delay_seconds:0,snapshot:{id:'transcript',segments:[],issues:[]}};
    const profile={depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''};
    const notes={status:'ready',editing:{version:0,selected:null,proposal:null,proposal_valid:false,sources_changed:false},preference:{version:1,model:'synthetic/local',digest:'a'.repeat(64),enabled:true},revision:{id:'revision',revision:1,created_at:created,profile,metadata:{model:'synthetic/local'},source_issues:[],content:{issues:[],coverage:[],blocks:Array.from({length:12},(_,index)=>({id:`block-${index}`,topic:`Lecture topic ${index+1}`,kind:'explanation',passages:[{id:`passage-${index}`,evidence_kind:'lecture_paraphrase',text:`Detailed synthetic notes for topic ${index+1}. `+('A supported explanation with definitions, examples, conditions, and readable study text. '.repeat(index===0?36:18)),sources:[]}]}))}},processing:{newer_transcript_pending:false,request_age_seconds:0},profile};
    let captureEpoch=0,manifestVersion=0,currentRun=null;
    const uploads=[],seals=[];
    await page.routeWebSocket('**/updates*',()=>{});
    await page.route('**/api/**',async route=>{
      const request=route.request(),url=new URL(request.url()),path=url.pathname;let body=[];
      if(path==='/api/session/open')body={owner_id:'synthetic-layout',csrf_token:'test',preview:true};
      else if(path==='/api/courses')body=[course];
      else if(path==='/api/courses/course/lectures')body=[lecture];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:course.name,settings:profile,processing_location:'local',transcript,notes};
      else if(path==='/api/deletions')body=[];
      else if(path.endsWith('/capture-runs')&&request.method()==='POST'){
        const start=request.postDataJSON();captureEpoch++;
        currentRun={id:start.run_id,state:'recording',sample_rate:start.sample_rate,saved_through_samples:0,complete:false,sealed:false,gaps:[],chunks:[]};manifestVersion=0;
        body={id:currentRun.id,capture_epoch:captureEpoch,gaps:[]};
      }else if(path.endsWith('/capture')||path.endsWith('/capture-runs'))body={available:true,capture_epoch:captureEpoch,keep_audio:false,runs:currentRun?[currentRun]:[]};
      else if(path.endsWith('/heartbeat'))body={grant_seconds:30};
      else if(path.includes('/chunks/')&&request.method()==='PUT'){
        const identity=JSON.parse(request.headers()['x-chunk-identity']);
        const receipt={...identity,chunk_id:`chunk-${identity.sequence}`,storage_state:'verified',manifest_version:++manifestVersion};
        uploads.push({identity,bytes:request.postDataBuffer().length});
        if(currentRun){currentRun.chunks.push({...receipt});currentRun.saved_through_samples+=identity.sample_count;}
        body=receipt;
      }else if(path.endsWith('/manifest'))body={manifest_version:manifestVersion,last_sequence:currentRun?.chunks.at(-1)?.sequence??null,final_sample_count:currentRun?.saved_through_samples??0,gaps:[]};
      else if(path.endsWith('/seal')&&request.method()==='POST'){
        const seal=request.postDataJSON();seals.push(seal);
        if(currentRun){currentRun.state='stopped';currentRun.sealed=true;currentRun.complete=true;currentRun.saved_through_samples=seal.final_sample_count;currentRun.gaps=seal.gaps;}
        body={manifest_version:manifestVersion+1,sealed:true};
      }else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/notes/stream'))return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify({active:false,text:''})+'\n\n'});
      else if(path.endsWith('/notes'))body=notes;
      else if(path.endsWith('/note-models'))body={models:[{name:'synthetic/local',digest:'a'.repeat(64),size:1}],available:true};
      else if(path.endsWith('/finalization'))body={cursor:2,edit_version:0,audio_removed:false,keep_audio:false,status:'audio_saved',history:[]};
      else if(path.endsWith('/study/learning'))body={revision_id:null,cards:[],omitted:0,issues:[]};
      else if(path.endsWith('/study/questions'))body={revision_id:null,blocks:[],preference_id:null,model:null,enabled:false,cloud:false,sets:[]};
      else if(path.endsWith('/provider-connections'))body={connections:[]};
      else if(path.endsWith('/terminology'))body={version:0,terms:[]};
      await route.fulfill({json:body});
    });

    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3018')+'/');
    const chooseRecordingDestination=page.locator('.recording-picker > summary');
    await chooseRecordingDestination.waitFor();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('.skip').evaluate(element=>element===document.activeElement),true,'the skip link is the first keyboard stop');
    assert.notEqual(await page.locator('.skip').evaluate(element=>getComputedStyle(element).outlineStyle),'none','keyboard focus is visible');
    assert.equal(await page.getByRole('button',{name:/Start recording/}).count(),0,'recording is unavailable until a destination is chosen');
    for(let stop=0;stop<30&&!await chooseRecordingDestination.evaluate(element=>element===document.activeElement);stop++)await page.keyboard.press('Tab');
    assert.equal(await chooseRecordingDestination.evaluate(element=>element===document.activeElement),true,'Record destination picker is reachable by keyboard');
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.recording-picker').evaluate(element=>element.open),true,'keyboard activates the destination picker');
    await page.locator('#record-course').selectOption('course');
    await page.locator('#record-lecture').selectOption('lecture');
    await page.getByRole('button',{name:'Use this lecture',exact:true}).click();
    await page.getByRole('heading',{name:'Your lecture notes'}).waitFor();
    await page.getByRole('region',{name:'Live transcript preview'}).waitFor();
    const mainNavigation=page.getByRole('navigation',{name:'Main lecture sections'});
    const moreNavigation=page.getByRole('navigation',{name:'Other lecture sections'});
    assert.deepEqual(await mainNavigation.getByRole('link').allTextContents(),['Notes','Finish']);
    assert.deepEqual(await moreNavigation.getByRole('link').allTextContents(),['Transcript','Materials','Capture','Visual notes','Flash Cards']);
    assert.equal(await page.getByText(/Ready when you are|Your Space to Learn/i).count(),0);
    assert.equal(await page.locator('#main-content > .capture-panel[aria-label="Deletion progress"]').count(),0);

    await page.evaluate(()=>{document.documentElement.scrollTop=document.documentElement.scrollHeight;});
    await page.waitForFunction(()=>window.scrollY>0);
    assert.equal(await page.locator('.workspace-header').evaluate(element=>Math.round(element.getBoundingClientRect().top)),0,'recording controls stay pinned after long notes scroll');
    assert.equal(await page.getByRole('button',{name:/Start recording/}).isVisible(),true);
    await page.evaluate(()=>window.scrollTo(0,0));

    await page.getByRole('button',{name:/Start recording/}).click();
    await page.locator('.recording-bar .recording-badge').waitFor();
    assert.equal(await page.evaluate(()=>window.__syntheticMicCalls),1,'only a synthetic oscillator stream was used');
    const recorderNode=page.locator('.recording-bar .capture-panel-compact');
    await recorderNode.evaluate(element=>element.dataset.recorderIdentity='kept');
    await page.getByRole('link',{name:'Transcript',exact:true}).click();
    await page.locator('.transcript-panel').waitFor({timeout:10000});
    await page.getByRole('link',{name:'Capture',exact:true}).click();
    await page.locator('.capture-detail-panel').waitFor();
    assert.equal(await recorderNode.getAttribute('data-recorder-identity'),'kept','the Capture panel shares the persistent recorder instance');
    assert.equal(await page.getByRole('button',{name:/Stop recording/}).isVisible(),true);
    await page.getByRole('link',{name:'Transcript',exact:true}).click();
    await page.locator('.transcript-panel').waitFor();
    await page.getByRole('link',{name:'Your library',exact:false}).click();
    await page.getByRole('heading',{name:'Your lecture library.'}).waitFor();
    assert.equal(await page.locator('.recording-bar .recording-badge').isVisible(),true,'recording remains active on home');
    assert.equal(await recorderNode.getAttribute('data-recorder-identity'),'kept','navigation kept the mounted recorder controller');
    await page.locator('.sidebar .course-link').filter({hasText:course.name}).click();
    await page.getByRole('heading',{name:course.name,exact:true}).waitFor();
    assert.equal(await page.locator('.recording-bar .recording-badge').isVisible(),true,'recording remains active on the course route');
    await page.setViewportSize({width:400,height:850});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'the narrow workspace has no horizontal overflow');
    await page.evaluate(()=>{document.documentElement.scrollTop=document.documentElement.scrollHeight;});
    await page.waitForFunction(()=>window.scrollY>0);
    assert.equal(await page.locator('.workspace-header').evaluate(element=>Math.round(element.getBoundingClientRect().top)),0,'narrow scrolling keeps Record controls visible');
    await page.setViewportSize({width:1280,height:760});
    await page.getByRole('button',{name:/Stop recording/}).click();
    await page.getByText(/This recording segment is saved/, {exact:false}).waitFor({timeout:20000});
    assert.ok(uploads.length>0&&uploads.every(item=>item.identity.sample_count>0&&item.bytes>44),'synthetic audio reached confirmed chunk uploads');
    assert.equal(seals.length,1);
    assert.equal(seals[0].final_sample_count,uploads.reduce((total,item)=>total+item.identity.sample_count,0));
    assert.equal(await page.evaluate(()=>window.__syntheticMicCalls),1);

    await page.getByRole('link',{name:'Open recording lecture',exact:true}).click();
    await page.getByRole('heading',{name:'Your lecture notes'}).waitFor();
    await page.getByRole('link',{name:'Notes',exact:true}).click();
    await page.getByRole('button',{name:'Edit notes',exact:true}).click();
    await page.getByLabel('Passage 1',{exact:true}).fill('A protected synthetic student draft.');
    await page.getByText(/Draft saved on this device/).waitFor();
    await page.getByRole('link',{name:'Finish',exact:true}).click();
    await page.getByRole('heading',{name:'Finalize and manage this lecture'}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Remove audio',exact:true}).isEnabled(),true,'data removal remains available under Finish');
    assert.deepEqual(errors,[]);
    console.log(`Persistent header, safe destination selection, home/course/transcript navigation during synthetic capture, ${uploads.length} verified synthetic audio chunk(s), 400px layout, keyboard focus, note draft and Finish passed.`);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
