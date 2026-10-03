// Notes-first responsive layout and protected UI behavior with synthetic API data only.
const playwrightDriver=process.env.NOTETAKER_PLAYWRIGHT_DRIVER||'../../.venv/Lib/site-packages/playwright/driver/package';
const {chromium}=require(playwrightDriver);
const assert=require('node:assert/strict');
const {mkdir}=require('node:fs/promises');
const path=require('node:path');

const lecture={id:'lecture',course_id:'course',title:'Cellular energy and ATP synthesis',status:'processed',audio_removed:false,created_at:'2026-10-03T12:00:00Z',update_cursor:4};
const profile={depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''};
const revision={id:'revision-1',revision:3,created_at:lecture.created_at,profile,metadata:{model:'synthetic/local'},student:false,source_issues:[],content:{issues:[],coverage:[{source_id:'source-1',disposition:'used',reason:''}],blocks:[
  {id:'block-1',kind:'explanation',topic:'How ATP synthase uses a proton gradient',passages:[{id:'passage-1',evidence_kind:'lecture_paraphrase',text:'ATP synthase lets protons flow down their electrochemical gradient across the inner mitochondrial membrane. The energy from that flow drives the enzyme to join ADP and inorganic phosphate into ATP.',sources:[{source_id:'source-1',quote:'The gradient powers the enzyme',occurrence:0}]}]},
  {id:'block-2',kind:'emphasis',topic:'Why the gradient matters',passages:[{id:'passage-2',evidence_kind:'lecture_paraphrase',text:'The proton-motive force stores energy temporarily, so electron transport and ATP formation remain coupled.',sources:[{source_id:'source-1',quote:'stores energy temporarily',occurrence:0}]}]},
  {id:'block-3',kind:'example',topic:'A useful comparison',passages:[{id:'passage-3',evidence_kind:'lecture_paraphrase',text:'The lecturer compared the gradient to water held behind a dam: flow can do work as it moves downhill.',sources:[{source_id:'source-1',quote:'water held behind a dam',occurrence:0}]}]},
]}};
const notes={status:'ready',editing:{version:2,selected:null,proposal:null,proposal_valid:true,sources_changed:false},preference:{version:1,model:'synthetic/local',digest:'a'.repeat(64),enabled:true},revision,processing:{newer_transcript_pending:false,request_age_seconds:0},profile,stale:false,error_code:null};
const transcript={speech_model:{state:'missing',name:null},status:'queued',counts:{due:1,running:0,completed:0,failed:0},errors:['model_unavailable'],preview:'The proton gradient stores energy between these steps.',waiting_for_audio:false,processing_delay_seconds:2.4,snapshot:{id:'transcript-1',sequence:1,stability:'provisional',issues:[],segments:[
  {id:'segment-1',text:'The gradient powers the enzyme.',start_sample:0,sample_rate:48000},
  {id:'segment-2',text:'Protons flow across the inner membrane.',start_sample:48000,sample_rate:48000},
  {id:'segment-3',text:'That motion supports ATP formation.',start_sample:96000,sample_rate:48000},
]}};

function contrastRatio(foreground,background){
  const luminance=color=>{const channels=color.match(/[\d.]+/g).slice(0,3).map(Number).map(value=>{value/=255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;});return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;};
  const a=luminance(foreground),b=luminance(background);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}

(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:900},deviceScaleFactor:1});
    const artifactDirectory=process.env.NOTETAKER_NOTES_FOCUS_ARTIFACTS||'.local/notes-focus-review';
    await mkdir(artifactDirectory,{recursive:true});
    const errors=[];let modelCalls=0;
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone access forbidden in this check');};});
    await page.routeWebSocket('**/updates*',()=>{});
    await page.route('**/api/**',async route=>{
      const request=route.request(),path=new URL(request.url()).pathname,method=request.method();let body=[];
      if(path==='/api/session/open')body={owner_id:'synthetic-notes-focus',csrf_token:'synthetic-csrf',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Synthetic biology',code:'BIO 204',created_at:lecture.created_at}];
      else if(path==='/api/courses/course/lectures')body=[lecture];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Synthetic biology',settings:{},processing_location:'local',update_cursor:4,transcript,notes};
      else if(path.endsWith('/capture')||path.endsWith('/capture-runs'))body={available:true,capture_epoch:1,keep_audio:false,runs:[]};
      else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/finalization'))body={cursor:4,edit_version:0,audio_removed:false,status:'complete',history:[]};
      else if(path.endsWith('/notes/stream'))return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify({active:false,text:''})+'\n\n'});
      else if(path.endsWith('/notes/model')&&method==='POST'){modelCalls++;body={saved:true};}
      else if(path.endsWith('/notes'))body=notes;
      else if(path.endsWith('/note-models'))body={models:[{name:'synthetic/local',digest:'a'.repeat(64),size:10}],available:true};
      else if(path.endsWith('/terminology'))body={version:1,terms:[]};
      else if(path.endsWith('/sources/source-1'))body={id:'source-1',text:'Synthetic lecture evidence for the proton gradient.',audio_url:'/api/audio/source-1',segment_number:1,start_sample:0,sample_rate:48000};
      else if(path.endsWith('/provider-connections'))body={connections:[]};
      else if(path.endsWith('/deletions'))body=[];
      await route.fulfill({json:body});
    });

    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3020')+'/#lecture/lecture/notes');
    await page.getByRole('heading',{name:'How ATP synthase uses a proton gradient'}).waitFor();
    await page.locator('html').evaluate(element=>element.setAttribute('data-theme','light'));
    const mainNavigation=page.getByRole('navigation',{name:'Main lecture sections'});
    const sideNavigation=page.getByRole('navigation',{name:'Other lecture sections'});
    assert.deepEqual(await mainNavigation.getByRole('link').allTextContents(),['Notes','Finish']);
    assert.deepEqual(await sideNavigation.getByRole('link').allTextContents(),['Transcript','Materials','Capture','Visual notes','Flash Cards']);
    assert.equal(await page.locator('.recording-picker[open], .recording-change[open]').count(),0,'Record stays available without opening the destination chooser');
    assert.equal(await page.locator('.processing-details').evaluate(element=>element.open),false,'processing controls are collapsed by default');
    await page.locator('.processing-details > summary').filter({hasText:'Transcription needs attention'}).waitFor();
    const noteText=page.locator('.note-pages-flow .study-text').first();
    const textBox=await noteText.boundingBox();
    console.log('desktop first-note position',textBox);
    assert.ok(textBox&&textBox.y<=700,'saved note text starts by 700px in the desktop viewport');
    assert.equal(await page.locator('.note-status').count(),0,'a ready saved revision has no blank status stripe');
    assert.equal(await noteText.isVisible(),true);
    const desktopLayout=await page.evaluate(()=>{
      const paper=document.querySelector('.note-paper').getBoundingClientRect();
      const preview=document.querySelector('.transcript-preview').getBoundingClientRect();
      const transcriptText=document.querySelector('.transcript-preview-scroll').getBoundingClientRect();
      const focus=document.querySelector('.settings-trigger').getBoundingClientRect();
      const toolbar=document.querySelector('.export-toolbar').getBoundingClientRect();
      const editing=document.querySelector('.note-editing').getBoundingClientRect();
      return {paper:{x:paper.x,y:paper.y,width:paper.width},preview:{x:preview.x,y:preview.y,width:preview.width,height:preview.height},transcriptHeight:transcriptText.height,toolbarHeight:toolbar.height,editingHeight:editing.height,settings:{x:focus.x,bottom:focus.bottom}};
    });
    assert.ok(desktopLayout.preview.x>desktopLayout.paper.x+desktopLayout.paper.width-2,'desktop transcript is in the secondary column');
    assert.ok(desktopLayout.preview.height<=170,`transcript preview is compact (${desktopLayout.preview.height}px)`);
    assert.ok(desktopLayout.transcriptHeight<=80,'only a few transcript lines are shown before scrolling');
    assert.ok(desktopLayout.toolbarHeight<=44,`export controls stay compact (${desktopLayout.toolbarHeight}px)`);
    assert.ok(desktopLayout.editingHeight<=44,`edit and revision actions stay compact (${desktopLayout.editingHeight}px)`);
    assert.ok(desktopLayout.settings.x<55&&desktopLayout.settings.bottom>850,'icon Settings stays at the bottom left');
    await page.screenshot({path:path.join(artifactDirectory,'notes-desktop-1280x900.png'),animations:'disabled'});

    const processing=page.locator('.processing-details');
    await processing.locator('summary').focus();await page.keyboard.press('Enter');
    assert.equal(await processing.evaluate(element=>element.open),true,'processing disclosure is keyboard operable');
    await page.getByText(/Saved audio is retained/).waitFor();
    await page.getByRole('button',{name:'Select speech model',exact:true}).waitFor();
    await processing.locator('summary').press('Enter');
    assert.equal(await processing.evaluate(element=>element.open),false);
    const notePreferences=page.locator('.note-preferences');
    await notePreferences.locator('summary').focus();await page.keyboard.press('Enter');
    assert.equal(await notePreferences.evaluate(element=>element.open),true,'notes model controls are keyboard operable');
    await page.locator('.model-picker-status').filter({hasText:'1 model available'}).waitFor();
    await page.getByLabel('Note model',{exact:true}).selectOption('synthetic/local');
    assert.equal(await page.getByRole('button',{name:'Regenerate notes',exact:true}).isEnabled(),true,'the saved note model remains selectable and applicable');
    await notePreferences.locator('summary').press('Enter');
    assert.equal(await notePreferences.evaluate(element=>element.open),false,'note settings return to their compact state');

    await page.evaluate(()=>localStorage.removeItem('notetaker:sidebar-hidden'));
    await page.setViewportSize({width:400,height:900});
    await page.reload();
    await page.getByRole('heading',{name:'How ATP synthase uses a proton gradient'}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Show library'}).getAttribute('aria-expanded'),'false','the library starts collapsed on a narrow lecture view');
    await page.getByText('ATP synthase lets protons flow down their electrochemical gradient',{exact:false}).waitFor();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'400px layout has no horizontal overflow');
    const narrowText=await page.locator('.note-pages-flow .study-text').first().boundingBox();
    console.log('narrow first-note position',narrowText);
    assert.ok(narrowText&&narrowText.y<=720,'saved note text starts by 720px on narrow screens');
    const narrowPreview=await page.locator('.transcript-preview').boundingBox();
    assert.ok(narrowPreview&&narrowPreview.height<=170,'narrow transcript remains compact');
    await page.screenshot({path:path.join(artifactDirectory,'notes-narrow-400px.png'),animations:'disabled'});
    const recordingBar=page.locator('.recording-bar');
    await page.evaluate(()=>window.scrollTo(0,700));
    const recordingPosition=await recordingBar.boundingBox();
    assert.ok(recordingPosition&&recordingPosition.y>=0&&recordingPosition.y<180,'persistent Record remains visible while scrolling on narrow screens');
    assert.equal(await page.getByText('Record',{exact:true}).isVisible(),true,'the recording entry point remains available while scrolling');
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.getByRole('button',{name:'Show library'}).click();
    assert.equal(await page.getByRole('button',{name:'Hide library'}).getAttribute('aria-expanded'),'true','the narrow library remains available through its accessible toggle');
    await page.getByRole('link',{name:/Your library/}).click();
    await page.getByRole('heading',{name:'Your lecture library.'}).waitFor();
    await page.getByRole('navigation',{name:'Workspace'}).getByRole('link',{name:/Synthetic biology/}).click();
    await page.getByRole('heading',{name:'Synthetic biology'}).waitFor();
    await page.evaluate(()=>{location.hash='#lecture/lecture/notes';});
    await page.getByRole('heading',{name:'How ATP synthase uses a proton gradient'}).waitFor();
    await page.getByRole('button',{name:'Hide library'}).click();
    await page.evaluate(()=>window.scrollTo(0,0));

    const themeResults=[];
    for(const theme of ['light','dark','pink','blue']){
      const result=await page.evaluate(theme=>{
        document.documentElement.dataset.theme=theme;
        const read=(selector)=>{
          const element=document.querySelector(selector),foreground=getComputedStyle(element).color;
          let parent=element,background='rgba(0, 0, 0, 0)';
          while(parent&&background==='rgba(0, 0, 0, 0)'){background=getComputedStyle(parent).backgroundColor;parent=parent.parentElement;}
          return {foreground,background};
        };
        return {notes:read('.note-pages-flow .study-text'),transcript:read('.transcript-preview-scroll')};
      },theme);
      for(const [surface,colors] of Object.entries(result)){
        const ratio=contrastRatio(colors.foreground,colors.background);
        assert.ok(ratio>=4.5,`${theme} ${surface} contrast ${ratio.toFixed(2)}:1`);
        themeResults.push(`${theme} ${surface} ${ratio.toFixed(2)}:1`);
      }
    }

    await page.getByRole('button',{name:/Source 1/}).first().click();
    await page.getByRole('region',{name:'Note source'}).filter({hasText:'Synthetic lecture evidence'}).waitFor();
    await page.getByRole('button',{name:'Close source'}).click();
    await page.getByRole('link',{name:'Finish',exact:true}).click();
    await page.getByRole('heading',{name:'Finalize and manage this lecture'}).waitFor();
    assert.deepEqual(await mainNavigation.getByRole('link').allTextContents(),['Notes','Finish']);
    await page.getByRole('link',{name:'Notes',exact:true}).click();
    await page.getByRole('button',{name:'Edit notes',exact:true}).click();
    await page.getByLabel('Passage 1',{exact:true}).fill('Protected synthetic student draft remains local.');
    await page.getByText(/Draft saved on this device/).waitFor();
    await page.getByRole('link',{name:'Finish',exact:true}).click();
    await page.getByRole('heading',{name:'Finalize and manage this lecture'}).waitFor();
    await page.getByRole('link',{name:'Notes',exact:true}).click();
    await page.getByRole('button',{name:/Restore draft from/}).waitFor();
    await page.getByRole('button',{name:/Restore draft from/}).click();
    assert.equal(await page.getByLabel('Passage 1',{exact:true}).inputValue(),'Protected synthetic student draft remains local.');
    notes.status='waiting_for_transcript';notes.revision=null;notes.editing={version:0,selected:null,proposal:null,proposal_valid:false,sources_changed:false};notes.preference=null;
    await page.reload();await page.locator('.note-placeholder').waitFor();
    assert.equal(await page.locator('.export-toolbar').count(),0,'the initial Notes state has no export toolbar');
    const emptyLayout=await page.evaluate(()=>{
      const paper=document.querySelector('.note-paper').getBoundingClientRect();
      const controls=document.querySelector('.note-controls').getBoundingClientRect();
      return {paper:{x:paper.x,width:paper.width},controls:{x:controls.x,width:controls.width},scrollWidth:document.documentElement.scrollWidth};
    });
    assert.ok(emptyLayout.controls.x>=emptyLayout.paper.x&&emptyLayout.controls.x<400,'empty-state note settings stack below the note placeholder');
    assert.ok(emptyLayout.scrollWidth<=400,'empty-state Notes has no implicit second column');
    await page.getByRole('button',{name:'Open notes settings'}).click();
    assert.equal(await page.locator('.note-preferences').evaluate(element=>element.open),true,'model settings remain one click away before the first saved revision');
    await page.getByLabel('Note model',{exact:true}).waitFor();
    assert.equal(modelCalls,0,'the layout check makes no model generation or preference write');
    assert.deepEqual(errors,[]);
    console.log(`Notes-first layout passed at 1280x900 and 400x900; only Notes/Finish are primary; compact transcript, collapsed speech diagnostics, model access, source links, persistent Record, keyboard access, draft recovery, and theme contrast passed (${themeResults.join('; ')}). Microphone and model calls: 0.`);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
