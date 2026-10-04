// Real React rendering: the cloud-processing confirmation closes and stays confirmed across navigation and reload.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.NOTETAKER_CHROMIUM});
  try{
    const page=await browser.newPage(),errors=[],choices=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    const origin=process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015';
    const lecture={id:'lecture',course_id:'course',title:'Synthetic consent lecture',status:'prepared',created_at:'2026-09-30T12:00:00Z'};
    const transcript={speech_model:{state:'ready'},status:'not_started',counts:{due:0,running:0,completed:0,failed:0},errors:[],preview:'',waiting_for_audio:false,processing_delay_seconds:0,snapshot:null};
    const notes={status:'choose_model',editing:{selected:null},preference:null,revision:null,processing:{},profile:{depth:'detailed',format:'topic_outline',instructions:'',detail_prompt:'',layout_prompt:''}};
    await page.routeWebSocket('**/updates*',()=>{});
    await page.route('**/api/**',async route=>{
      const request=route.request(),path=new URL(request.url()).pathname;let body=[];
      if(path==='/api/session/open')body={owner_id:'synthetic-consent',csrf_token:'test',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Synthetic course',code:'TEST',created_at:lecture.created_at}];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Synthetic course',settings:{},update_cursor:0,transcript,notes};
      else if(path.endsWith('/lectures'))body=[lecture];
      else if(path.endsWith('/finalization'))body={cursor:0,edit_version:0,audio_removed:false,keep_audio:false,status:'prepared',history:[]};
      else if(path.endsWith('/transcript'))body=transcript;
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:0,keep_audio:false,runs:[]};
      else if(path.endsWith('/note-models'))body={models:[{name:'qwen3:4b',digest:'a'.repeat(64),size:1},{name:'openai/gpt-synthetic',digest:'b'.repeat(64),size:0,provider:'openai'}],available:true};
      else if(path.endsWith('/notes/model')){const choice=request.postDataJSON();choices.push(choice);notes.preference={version:choice.expected_version+1,model:choice.model,digest:'b'.repeat(64),enabled:choice.enabled};notes.status='waiting_for_transcript';body=notes.preference;}
      else if(path.endsWith('/notes/stream'))return route.fulfill({contentType:'text/event-stream',body:'data: {"active":false,"text":""}\n\n'});
      else if(path.endsWith('/notes'))body=notes;
      await route.fulfill({json:body});
    });
    const prompt=()=>page.getByRole('checkbox',{name:/I understand this sends the lecture transcript/});
    const confirmed=()=>page.getByText('Cloud processing confirmed for openai.');
    await page.goto(origin+'/#lecture/lecture/notes');
    await page.getByLabel('Note model').selectOption('openai/gpt-synthetic');
    await prompt().click();
    await confirmed().waitFor();
    assert.equal(await prompt().count(),0); // The prompt closes once confirmed.
    await page.getByRole('button',{name:'Start automatic notes'}).click();
    await page.waitForFunction(()=>document.body.innerText.includes('Apply note preferences'));
    assert.equal(choices.at(-1).cloud_consent,true);
    // Leave the lecture section and come back: still confirmed, nothing re-asks.
    await page.getByRole('link',{name:'Transcript',exact:true}).click();
    await page.getByRole('link',{name:'Notes',exact:true}).click();
    await confirmed().waitFor();assert.equal(await prompt().count(),0);
    await page.reload();
    await confirmed().waitFor();assert.equal(await prompt().count(),0);
    // Withdrawing brings the prompt back and blocks applying the cloud model.
    await page.getByRole('button',{name:'Withdraw'}).click();
    await prompt().waitFor();
    assert.equal(await prompt().isChecked(),false);
    assert.deepEqual(errors,[]);
    console.log('Cloud consent closes on confirmation and persists across navigation and reload; withdrawal restores it.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
