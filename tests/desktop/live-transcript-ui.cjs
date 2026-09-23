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
    const transcript={status:'queued',counts:{due:1,running:0,completed:0,failed:0},errors:['model_unavailable'],preview:'',waiting_for_audio:false,processing_delay_seconds:8,snapshot:null};
    const notes={status:'waiting_for_transcript',editing:{selected:null},preference:null,revision:null,processing:{},profile:{depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''}};
    let socket;
    await page.routeWebSocket('**/updates*',value=>{socket=value;});
    await page.route('**/api/**',async route=>{
      const path=new URL(route.request().url()).pathname;let body=[];
      if(path==='/api/session/open')body={owner_id:'synthetic-live',csrf_token:'test',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Synthetic course',code:'TEST',created_at:lecture.created_at}];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Synthetic course',settings:{},update_cursor:0,transcript,notes};
      else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:1,runs:[]};
      else if(path.endsWith('/notes'))body=notes;
      else if(path.endsWith('/note-models'))body={models:[],available:true};
      else if(path.endsWith('/notes/stream'))return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify({active:true,text:'A streamed study explanation.'})+'\n\n'});
      await route.fulfill({json:body});
    });
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#lecture/lecture/transcript');
    await page.locator('.live-progress').filter({hasText:'waiting for a speech model'}).waitFor();
    await page.locator('.transcript-panel').filter({hasText:'Choose a local speech model folder'}).waitFor();
    transcript.errors=[];transcript.status='processing';transcript.preview='Partial recognized words <script> are safe text.';
    socket.send(JSON.stringify({schema_version:1,kind:'heartbeat',cursor:0}));
    await page.getByRole('region',{name:'Speech being transcribed'}).filter({hasText:transcript.preview}).waitFor();
    transcript.preview='';transcript.status='listening';transcript.counts={due:0,running:0,completed:1,failed:0};
    transcript.snapshot={id:'snapshot',sequence:1,stability:'provisional',issues:[],segments:[{id:'version',segment_id:'segment',revision:1,text:'Saved recognized words.',author:'machine',segment_number:1,sample_rate:48000,start_sample:0,end_sample:48000,confidence:{value:null},audio_url:'/api/audio'}]};
    socket.send(JSON.stringify({schema_version:1,kind:'heartbeat',cursor:0}));
    await page.getByText('Saved recognized words.',{exact:true}).waitFor();
    await page.getByRole('region',{name:'Speech being transcribed'}).waitFor({state:'detached'});
    await page.getByRole('tab',{name:/Study notes/}).click();
    await page.getByRole('region',{name:'Notes being written'}).filter({hasText:'A streamed study explanation.'}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('Missing-model guidance, live speech preview, saved transcript and note streaming passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
