// Synthetic API responses in the actual React workspace; no microphone/provider calls.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
const {mkdir}=require('node:fs/promises');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    const lecture={id:'lecture',course_id:'course',title:'Energy transfer',status:'stopped',audio_removed:false,created_at:'2026-09-16T12:00:00Z'};
    const original={id:'q1',kind:'flashcard',objective:'definition',question:'What does ATP transfer?',answer:'ATP transfers energy, but is not long-term energy storage.',citations:[{source_id:'s1',quote:'ATP transfers energy'}],version:0,revision_id:'set',student_edited:false,quality:{support:-1,answerability:-1,clarity:-1,usefulness:-1},feedback:'',review:{version:0,rating:'unreviewed'}};
    let card=structuredClone(original),history=[structuredClone(original)],sets=[],generationCalls=[],editCalls=[],failGeneration=true,conflict=true,reads=0,stale=false;
    const summary=()=>({id:'set',topic:'ATP',model:'openai/synthetic',status:reads<2?'running':'completed',error_code:null,preview:reads<2?'What does ATP transfer?':'',created_at:lecture.created_at,count:reads<2?0:1});
    await page.route('**/api/**',async route=>{
      const req=route.request(),path=new URL(req.url()).pathname;let body=[],status=200;
      if(path==='/api/session/open')body={owner_id:'synthetic',csrf_token:'csrf',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Biology',code:'BIO',created_at:lecture.created_at}];
      else if(path.endsWith('/courses/course/lectures'))body=[lecture];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Biology',settings:{},update_cursor:0,transcript:{processing_delay_seconds:0}};
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:0,runs:[]};
      else if(path.endsWith('/study/learning'))body={revision_id:'note',cards:[],omitted:0,issues:[]};
      else if(path.endsWith('/terminology'))body={version:0,terms:[]};
      else if(path.endsWith('/study/questions')){
        if(req.method()==='POST'){
          assert.equal(req.headers()['x-csrf-token'],'csrf');
          generationCalls.push({key:req.headers()['idempotency-key'],body:req.postDataJSON()});
          assert.equal(req.postDataJSON().cloud_consent,true);
          if(failGeneration){failGeneration=false;status=503;body={error:{message:'Synthetic queue failure'}};}
          else{sets=[summary()];body=summary();status=202;}
        }else body={revision_id:'note',blocks:[{id:'b1',topic:'ATP'}],preference_id:'pref',model:'openai/synthetic',enabled:true,cloud:true,sets:sets.map(()=>summary())};
      }else if(path.endsWith('/study/questions/set')){
        reads++;body={...summary(),revision_id:'note',stale,questions:reads<2?[]:[card],sources:[{id:'s1',text:original.answer,label:'Biology source'}],issues:[],metadata:{},quality_counts:{}};
      }else if(path.endsWith('/set/q1/edits')){
        const data=req.postDataJSON();editCalls.push(data);assert.equal(req.headers()['x-csrf-token'],'csrf');
        if(conflict){conflict=false;card={...card,version:1,revision_id:'external',question:'What is transferred by ATP?'};history.unshift(structuredClone(card));status=409;body={error:{message:'This question changed in another window. Your draft is preserved; load the saved version to compare.'}};}
        else{assert.equal(data.expected_version,card.version);card={...card,...data,version:card.version+1,revision_id:'edit-'+(card.version+1),student_edited:true,review:{version:0,rating:'unreviewed'}};history.unshift(structuredClone(card));body=card;}
      }else if(path.endsWith('/set/q1/history'))body=history;
      else if(path.endsWith('/set/q1/reviews')){
        const data=req.postDataJSON();assert.equal(data.question_revision,card.revision_id);assert.equal(data.expected_version,card.review.version);card={...card,review:{version:card.review.version+1,rating:data.rating}};body=card.review;
      }
      await route.fulfill({status,json:body});
    });
    await page.routeWebSocket('**/updates*',socket=>socket.onMessage(()=>{}));
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#lecture/lecture/study');
    await page.getByLabel('App theme').selectOption('dark');
    const region=page.getByRole('region',{name:'Generated questions',exact:true});
    await region.getByText('Model: openai/synthetic',{exact:true}).waitFor();
    assert.ok(await region.getByRole('button',{name:'Generate new question set',exact:true}).isDisabled());
    await region.getByRole('checkbox').check();
    await region.getByLabel('Study focus (optional)').fill('Qualifications');
    await region.getByRole('button',{name:'Generate new question set',exact:true}).click();
    await region.getByRole('button',{name:'Retry question request',exact:true}).click();
    await region.getByText('Unvalidated generation preview — not saved questions',{exact:true}).waitFor();
    await region.getByRole('button',{name:'Reveal generated answer',exact:true}).click();
    assert.deepEqual(generationCalls[0],generationCalls[1]);
    await region.getByText('Biology source',{exact:true}).click();
    await region.getByRole('button',{name:'Confident',exact:true}).click();
    await region.getByText('Self-assessment saved.',{exact:true}).waitFor();
    await region.getByText('Edit question and evaluate quality',{exact:true}).click();
    await region.getByLabel('Question wording',{exact:true}).fill('What does ATP transfer, and what is its limitation?');
    await region.getByRole('button',{name:'Save question revision',exact:true}).click();
    await region.getByRole('alert').filter({hasText:'changed in another window'}).waitFor();
    assert.equal(await region.getByLabel('Question wording',{exact:true}).inputValue(),'What does ATP transfer, and what is its limitation?');
    await region.getByRole('button',{name:'Load saved versions to compare',exact:true}).click();
    await region.getByRole('button',{name:'Keep my draft against this version',exact:true}).click();
    for(const label of ['Source support','Answerability','Clarity','Study usefulness'])await region.getByLabel(label,{exact:false}).selectOption(label==='Clarity'?'1':'2');
    await region.getByRole('button',{name:'Save question revision',exact:true}).click();
    await region.getByText('Question revision and quality review saved.',{exact:true}).waitFor();
    assert.ok(await region.getByRole('button',{name:'Confident',exact:true}).isDisabled());
    await region.getByLabel('Clarity',{exact:false}).selectOption('2');
    await region.getByRole('button',{name:'Save question revision',exact:true}).click();
    await region.getByRole('button',{name:'Confident',exact:true}).click();
    await region.getByText('Self-assessment saved.',{exact:true}).waitFor();
    assert.equal(editCalls[1].expected_version,1);
    await region.getByRole('button',{name:'Load saved versions to compare',exact:true}).click();
    await region.getByText('Earlier versions / undo',{exact:true}).click();
    await region.getByRole('button',{name:'Load version 0 into draft',exact:true}).click();
    assert.equal(await region.getByLabel('Question wording',{exact:true}).inputValue(),original.question);
    await region.getByRole('button',{name:'Save question revision',exact:true}).click();
    await region.getByText('Question revision and quality review saved.',{exact:true}).waitFor();
    stale=true;
    await region.getByRole('button',{name:'Refresh question setup and set',exact:true}).click();
    await region.getByText(/This set uses an earlier note revision/).waitFor();
    await region.getByRole('button',{name:'Reveal generated answer',exact:true}).click();
    assert.ok(await region.getByRole('button',{name:'Confident',exact:true}).isDisabled());
    await mkdir('.local/questions-review',{recursive:true});
    await region.screenshot({path:'.local/questions-review/midnight.png'});
    await page.setViewportSize({width:400,height:900});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await region.screenshot({path:'.local/questions-review/narrow.png'});
    assert.deepEqual(errors,[]);
    console.log('Question UI passed: cloud consent, request retry identity, preview, cited reveal, self-assessment, edit conflict/compare, quality gating, history/undo, stale-source gate, Midnight and narrow layout.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
