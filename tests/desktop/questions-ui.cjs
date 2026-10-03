// Actual React UI with synthetic API responses; no microphone or model is used.
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const {mkdir}=require('node:fs/promises');
const python=path.resolve(__dirname,'../../.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const pythonPackages=execFileSync(python,['-c','import sysconfig; print(sysconfig.get_path("purelib"))'],{encoding:'utf8'}).trim();
const {chromium}=require(path.join(pythonPackages,'playwright','driver','package'));
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};});
    const lecture={id:'lecture',course_id:'course',title:'Energy transfer',status:'stopped',audio_removed:false,created_at:'2026-10-03T12:00:00Z'};
    const original={id:'q1',kind:'flashcard',objective:'definition',question:'What does ATP transfer?',answer:'ATP transfers energy, but is not long-term energy storage.',citations:[{source_id:'s1',quote:'ATP transfers energy'}],version:0,revision_id:'set',student_edited:false,quality:{support:-1,answerability:-1,clarity:-1,usefulness:-1},feedback:'',review:{version:0,rating:'unreviewed'}};
    let card=structuredClone(original),history=[structuredClone(original)],sets=[],generationCalls=[],editCalls=[],failGeneration=true,conflict=true,reads=0,stale=false,hasNotes=true;
    const summary=()=>({id:'set',topic:'Flash cards from saved notes',prompt:generationCalls.at(-1)?.body.prompt||'Make concise cards with qualifications.',model:'qwen3:4b',status:'running',error_code:null,preview:reads<2?'Preparing supported cards…':'',created_at:lecture.created_at,count:reads<2?0:1});
    const forbiddenRequests=[];
    await page.route('**/api/**',async route=>{
      const req=route.request(),path=new URL(req.url()).pathname;let body=[],status=200;
      if(path==='/api/session/open')body={owner_id:'synthetic',csrf_token:'csrf',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Biology',code:'BIO',created_at:lecture.created_at}];
      else if(path.endsWith('/courses/course/lectures'))body=[lecture];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Biology',settings:{},update_cursor:0,transcript:{processing_delay_seconds:0}};
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:0,runs:[]};
      else if(path.endsWith('/materials'))body=[];
      else if(path.endsWith('/study/catch-up')||path.endsWith('/study/learning')){forbiddenRequests.push(path);status=404;body={detail:'retired'};}
      else if(path.endsWith('/study/questions')){
        if(req.method()==='POST'){
          assert.equal(req.headers()['x-csrf-token'],'csrf');
          generationCalls.push({key:req.headers()['idempotency-key'],body:req.postDataJSON()});
          assert.equal(generationCalls.at(-1).body.cloud_consent,false);
          if(failGeneration){failGeneration=false;status=503;body={error:{message:'Synthetic queue failure'}};}
          else{sets=[summary()];body=summary();status=202;}
        }else body={revision_id:hasNotes?'note':null,has_notes:hasNotes,omitted_blocks:0,preference_id:'pref',model:'qwen3:4b',enabled:true,cloud:false,sets};
      }else if(path.endsWith('/study/questions/set')){
        reads++;const running=reads<2;
        body={...summary(),status:running?'running':'completed',revision_id:'note',stale,questions:running?[]:[card],sources:[{id:'s1',text:original.answer,label:'Biology source'}],issues:[],metadata:{},quality_counts:{reviewed:0,needs_work:0,total:1}};
      }else if(path.endsWith('/set/q1/edits')){
        const data=req.postDataJSON();editCalls.push(data);assert.equal(req.headers()['x-csrf-token'],'csrf');
        if(conflict){conflict=false;status=409;card={...card,version:1,revision_id:'external',question:'What is transferred by ATP?'};history.unshift(structuredClone(card));body={error:{message:'This question changed in another window. Your draft is preserved; load the saved version to compare.'}};}
        else{assert.equal(data.expected_version,card.version);card={...card,...data,version:card.version+1,revision_id:'edit-'+(card.version+1),student_edited:true,review:{version:0,rating:'unreviewed'}};history.unshift(structuredClone(card));body=card;}
      }else if(path.endsWith('/set/q1/history'))body=history;
      else if(path.endsWith('/set/q1/reviews')){
        const data=req.postDataJSON();assert.equal(data.question_revision,card.revision_id);assert.equal(data.expected_version,card.review.version);card={...card,review:{version:card.review.version+1,rating:data.rating}};body=card.review;
      }
      await route.fulfill({status,json:body});
    });
    await page.routeWebSocket('**/updates*',socket=>socket.onMessage(()=>{}));
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#lecture/lecture/study');
    await page.getByRole('tab',{name:'Flash Cards',exact:true}).waitFor();
    await page.getByLabel('App theme').selectOption('dark');
    const region=page.getByRole('region',{name:'Flash cards',exact:true});
    await region.getByText('Selected model:').waitFor();
    assert.equal(await page.getByRole('tab',{name:'Study tools',exact:true}).count(),0);
    assert.equal(await region.getByText('Catch Me Up',{exact:false}).count(),0);
    assert.equal(generationCalls.length,0,'opening the tab does not generate cards');

    await region.getByRole('button',{name:'Create flash cards',exact:true}).click();
    const dialog=page.getByRole('dialog',{name:'Create flash cards'});
    const submit=dialog.getByRole('button',{name:'Generate flash cards',exact:true});
    assert.ok(await submit.isDisabled());
    await dialog.screenshot({path:'.local/questions-review/prompt.png'});
    await dialog.getByRole('button',{name:'Cancel',exact:true}).click();
    await page.getByRole('tab',{name:'Materials',exact:true}).click();
    await page.getByRole('heading',{name:'Lecture materials',exact:true}).waitFor();
    await page.getByRole('tab',{name:'Flash Cards',exact:true}).click();
    await region.getByRole('button',{name:'Create flash cards',exact:true}).waitFor();
    assert.equal(generationCalls.length,0,'opening, closing and tab switching do not generate cards');
    assert.deepEqual(forbiddenRequests,[],'retired study endpoints are not called');

    await region.getByRole('button',{name:'Create flash cards',exact:true}).click();
    const prompt=dialog.getByLabel('What should the cards help you study?');
    await prompt.fill('   ');
    assert.ok(await submit.isDisabled(),'blank or whitespace instructions cannot be submitted');
    assert.equal(generationCalls.length,0);
    await prompt.fill('Make concise cards. Include every condition and exception.');
    await submit.click();
    await dialog.getByRole('alert').filter({hasText:'Synthetic queue failure'}).waitFor();
    await dialog.getByRole('button',{name:'Retry sending the same request',exact:true}).click();
    assert.deepEqual(generationCalls[0],generationCalls[1],'network retry preserves idempotency key and prompt');
    assert.equal(generationCalls[1].body.prompt,'Make concise cards. Include every condition and exception.');
    await region.getByRole('button',{name:'Reveal generated answer',exact:true}).waitFor({timeout:10000});
    await region.getByText('Unvalidated generation preview',{exact:false}).count().then(count=>assert.equal(count,0));
    await region.getByRole('button',{name:'Reveal generated answer',exact:true}).click();
    await region.locator('article.flash-card > div').getByText('ATP transfers energy, but is not long-term energy storage.',{exact:true}).first().waitFor();
    await region.locator('summary').filter({hasText:'Biology source'}).click();
    assert.equal(await region.locator('blockquote').textContent(),'ATP transfers energy');

    await region.getByRole('button',{name:'Confident',exact:true}).click();
    await region.getByText('Self-assessment saved.',{exact:true}).waitFor();
    await region.getByText('Edit question and evaluate quality',{exact:true}).click();
    await region.getByLabel('Question wording',{exact:true}).fill('What does ATP transfer, and what limitation is stated?');
    await region.getByRole('button',{name:'Save question revision',exact:true}).click();
    await region.getByRole('alert').filter({hasText:'changed in another window'}).waitFor();
    assert.equal(await region.getByLabel('Question wording',{exact:true}).inputValue(),'What does ATP transfer, and what limitation is stated?');
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

    stale=true;await page.reload();
    const refreshed=page.getByRole('region',{name:'Flash cards',exact:true});
    await refreshed.getByText(/earlier saved note revision/).waitFor();
    await refreshed.getByRole('button',{name:'Reveal generated answer',exact:true}).click();
    assert.ok(await refreshed.getByRole('button',{name:'Confident',exact:true}).isDisabled());
    assert.equal(generationCalls.length,2,'reopening and note revision refresh never start generation');
    await mkdir('.local/questions-review',{recursive:true});
    await refreshed.screenshot({path:'.local/questions-review/midnight.png'});
    await page.setViewportSize({width:400,height:900});
    await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth,{timeout:2000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await refreshed.screenshot({path:'.local/questions-review/narrow.png'});
    hasNotes=false;sets=[];
    await page.reload();
    const emptyRegion=page.getByRole('region',{name:'Flash cards',exact:true});
    await emptyRegion.getByText('Save source-linked notes before creating flash cards.',{exact:true}).waitFor();
    assert.ok(await emptyRegion.getByRole('button',{name:'Create flash cards',exact:true}).isDisabled());
    assert.deepEqual(errors,[]);
    console.log('Flash Cards UI passed: prompt dialog and empty state, prompt-only generation, blank-prompt refusal, no generation on open/tab switch/reload, CSRF and idempotent retry, local model display, cited reveal, self-assessment, edit conflict/history, stale-source gate and narrow layout.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
