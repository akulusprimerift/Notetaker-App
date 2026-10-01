// Real React rendering of audio retention controls with synthetic network responses; no microphone.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.NOTETAKER_CHROMIUM});
  try{
    const page=await browser.newPage(),errors=[],puts=[],finals=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    const lecture={id:'lecture',course_id:'course',title:'Synthetic retention lecture',status:'audio_saved',created_at:'2026-09-30T12:00:00Z'};
    const transcript={speech_model:{state:'ready'},status:'processed',counts:{due:0,running:0,completed:2,failed:0},errors:[],preview:'',waiting_for_audio:false,processing_delay_seconds:0,snapshot:null};
    const notes={status:'waiting_for_transcript',editing:{selected:null},preference:null,revision:null,processing:{},profile:{depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''}};
    const chunk=(sequence,released)=>({chunk_id:'c'+sequence,sequence,storage_state:'verified',start_sample:sequence*32000,sample_count:32000,released});
    const capture={available:true,capture_epoch:1,keep_audio:false,runs:[{id:'run',state:'stopped',sample_rate:16000,saved_through_samples:96000,complete:true,sealed:true,gaps:[],chunks:[chunk(0,true),chunk(1,true),chunk(2,false)]}]};
    await page.routeWebSocket('**/updates*',()=>{});
    await page.route('**/api/**',async route=>{
      const request=route.request(),path=new URL(request.url()).pathname;let body=[];
      if(path==='/api/session/open')body={owner_id:'synthetic-retention',csrf_token:'test',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Synthetic course',code:'TEST',created_at:lecture.created_at}];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Synthetic course',settings:{},update_cursor:0,transcript,notes};
      else if(path.endsWith('/lectures'))body=[lecture];
      else if(path.endsWith('/audio-retention')){assert.equal(request.headers()['x-csrf-token'],'test');puts.push(request.postDataJSON());capture.keep_audio=request.postDataJSON().keep_audio;body={keep_audio:capture.keep_audio};}
      else if(path.endsWith('/finalization')&&request.method()==='POST'){finals.push(request.postDataJSON());body={id:'f',status:'speech',issues:[],snapshot_id:null,created_at:lecture.created_at};}
      else if(path.endsWith('/finalization'))body={cursor:3,edit_version:0,audio_removed:false,keep_audio:capture.keep_audio,status:'audio_saved',history:[]};
      else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/capture'))body=capture;
      else if(path.endsWith('/notes'))body=notes;
      else if(path.endsWith('/note-models'))body={models:[],available:true};
      await route.fulfill({json:body});
    });
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#lecture/lecture/capture');
    const toggle=page.getByRole('checkbox',{name:/Keep lecture audio after transcription/});
    await toggle.waitFor();
    assert.equal(await toggle.isChecked(),false);
    await page.getByText('0:04 of transcribed audio was deleted to save storage.').waitFor();
    await page.getByText('Listen to saved audio').click();
    assert.equal(await page.getByRole('button',{name:/^Play /}).count(),1); // Released chunks are not offered.
    await toggle.click(); // Controlled: the box reflects the server-confirmed setting.
    await page.waitForFunction(()=>document.body.innerText.includes('Audio stays saved for playback'));
    assert.deepEqual(puts,[{keep_audio:true}]);
    // Finish: kept audio defaults to keeping; the student can choose to delete all of it.
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#lecture/lecture/finalize');
    await page.getByRole('button',{name:'Finalize lecture'}).click();
    const keepAll=page.getByRole('radio',{name:/Keep all remaining audio/}),deleteAll=page.getByRole('radio',{name:/Delete all audio once/});
    assert.equal(await keepAll.isChecked(),true);
    await deleteAll.check();
    await page.getByRole('button',{name:'Confirm'}).click();
    await page.waitForFunction(()=>!document.querySelector('[aria-label="Confirm data action"]'));
    assert.equal(finals.length,1);assert.equal(finals[0].discard_audio,true);assert.equal(finals[0].available_only,false);
    assert.deepEqual(errors,[]);
    console.log('Audio retention toggle, released-chunk playback filtering and finalization audio choice passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
