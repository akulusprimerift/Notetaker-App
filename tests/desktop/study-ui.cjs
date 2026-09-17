// Actual React UI, mocked API and saved audio; never opens the microphone.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
const {mkdir}=require('node:fs/promises');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden in this test');};});
    const lecture={id:'lecture',course_id:'course',title:'Energy transfer',status:'stopped',audio_removed:false,created_at:'2026-09-15T12:00:00Z'};
    let marks=[],attempts=[],terms={version:1,terms:['ATP']},conflict=true,catchups=0,failMark=true;
    let review={version:0,rating:'unreviewed',reviewed_at:null},reviewAttempts=[],failReview=true,conflictReview=false;
    await page.route('**/api/**',async route=>{
      const request=route.request(),path=new URL(request.url()).pathname;let body=[],status=200;
      if(path==='/api/session/open')body={owner_id:'synthetic-study',csrf_token:'test-csrf',preview:true};
      else if(path==='/api/courses')body=[{id:'course',name:'Biology',code:'BIO',created_at:lecture.created_at}];
      else if(path==='/api/courses/course/lectures')body=[lecture];
      else if(path.endsWith('/snapshot'))body={lecture,course_name:'Biology',settings:{},update_cursor:0,transcript:{processing_delay_seconds:0}};
      else if(path.endsWith('/capture'))body={available:true,capture_epoch:1,runs:[{id:'run',state:'stopped',sample_rate:48000,saved_through_samples:1440000,complete:true,sealed:true,gaps:[],chunks:[]}]};
      else if(path.endsWith('/study/marks')){
        if(request.method()==='POST'){
          assert.equal(request.headers()['x-csrf-token'],'test-csrf');
          attempts.push({key:request.headers()['idempotency-key'],body:request.postDataJSON()});
          if(failMark){failMark=false;status=503;body={error:{message:'Synthetic connection failure'}};}
          else{marks=[{id:'mark',...request.postDataJSON(),sample_rate:48000,recording_number:1,label:'Important to me',version:1,removed:false,awaiting_audio:false}];body=marks[0];}
        }else body=marks;
      }else if(path.endsWith('/study/marks/mark')){marks[0]={...marks[0],removed:request.postDataJSON().removed,version:marks[0].version+1};body=marks[0];}
      else if(path.endsWith('/study/catch-up')){
        catchups++;
        body={snapshot_id:'snapshot',revision_id:'note',message:'Excerpts from saved notes for this interval.',start_seconds:0,end_seconds:30,recording_number:1,omitted_stale:0,issues:[],items:[{topic:'Energy transfer',text:'ATP transfers energy, but is not long-term energy storage.',student_edited:false,source_ids:['source'],kind:'saved_note',passage_id:'passage'}],sources:[{id:'source',text:'ATP transfers energy, but is not long-term energy storage.',segment_number:1,start_sample:48000,sample_rate:48000,audio_url:'/api/source/audio'}]};
      }else if(path.endsWith('/study/learning')){
        body={revision_id:'saved-note',omitted:1,issues:[],cards:[{id:'energy',topic:'Energy transfer',prompt:'Explain energy transfer, including qualifications.',passages:[{text:'ATP transfers energy, but is not long-term energy storage.',student_edited:true}],sources:[{id:'s',text:'ATP is not long-term energy storage.',label:'Biology source'}],review}]};
      }else if(path.endsWith('/study/learning/reviews')){
        assert.equal(request.headers()['x-csrf-token'],'test-csrf');
        const data=request.postDataJSON();reviewAttempts.push({key:request.headers()['idempotency-key'],body:data});
        if(failReview){failReview=false;status=503;body={error:{message:'Synthetic assessment failure'}};}
        else if(conflictReview){conflictReview=false;status=409;body={error:{message:'This assessment changed in another window. Refresh practice before trying again.'}};}
        else{assert.equal(data.expected_version,review.version);review={version:review.version+1,rating:data.rating,reviewed_at:'2026-09-16T12:00:00Z'};body=review;}
      }else if(path.endsWith('/study/questions')){
        body={revision_id:'saved-note',blocks:[],preference_id:null,model:null,enabled:false,cloud:false,sets:[]};
      }else if(path.endsWith('/terminology')){
        if(request.method()==='POST'){
          const data=request.postDataJSON();assert.equal(request.headers()['x-csrf-token'],'test-csrf');
          if(conflict){conflict=false;terms={version:2,terms:['ADP']};status=409;body={error:{message:'Course terms changed in another window. Your draft is still here.'}};}
          else{assert.equal(data.expected_version,2);terms={version:3,terms:data.terms};body=terms;}
        }else body=terms;
      }
      await route.fulfill({status,json:body});
    });
    await page.routeWebSocket('**/updates*',socket=>socket.onMessage(()=>{}));
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#lecture/lecture/study');
    await page.getByRole('heading',{name:'Pick up the thread.'}).waitFor();
    await page.getByLabel('App theme').selectOption('dark');
    await page.getByRole('button',{name:'★ Mark Important',exact:true}).click();
    await page.getByRole('button',{name:'Retry saving marker',exact:true}).click();
    await page.getByText('Marked important. Review it in Study tools.',{exact:true}).waitFor();
    assert.equal(attempts.length,2);assert.deepEqual(attempts[0],attempts[1]);assert.equal(attempts[0].body.sample,1440000);
    await page.getByRole('button',{name:'Review this moment',exact:true}).click();
    const result=page.getByRole('region',{name:'Catch-up result'});await result.waitFor();
    await result.locator('summary').click();assert.equal(await result.locator('audio').getAttribute('preload'),'none');
    await page.evaluate(()=>window.dispatchEvent(new CustomEvent('lecture-snapshot',{detail:{lecture:'lecture',snapshot:{}}})));
    assert.equal(catchups,1);assert.match(await result.innerText(),/not long-term energy storage/);
    await page.getByRole('button',{name:'Remove marker',exact:true}).click();
    await page.getByRole('button',{name:'Undo marker removal',exact:true}).click();
    await page.getByRole('button',{name:'Review this moment',exact:true}).waitFor();assert.equal(marks[0].removed,false);
    const draft=page.getByLabel('Terms, one per line');await draft.fill('mitochondria\nATP');
    await page.getByRole('button',{name:'Save course terms',exact:true}).click();await page.getByRole('alert').filter({hasText:'Course terms changed'}).waitFor();
    assert.equal(await draft.inputValue(),'mitochondria\nATP');
    await page.getByRole('button',{name:'Load saved terms',exact:true}).click();await page.getByText('Compare saved terms (version 2)',{exact:true}).waitFor();
    assert.equal(await draft.inputValue(),'mitochondria\nATP');
    await page.getByRole('button',{name:'Save course terms',exact:true}).click();await page.getByText('Course terms saved for future transcription batches.',{exact:true}).waitFor();
    assert.deepEqual(terms.terms,['mitochondria','ATP']);
    const learning=page.getByRole('region',{name:'Recall practice'});
    assert.equal(await learning.getByText('Answer from saved notes',{exact:true}).count(),0);
    await learning.getByLabel('Practice answer (optional)').fill('My recall attempt');
    await learning.getByRole('button',{name:'Reveal saved answer',exact:true}).click();
    await learning.getByText('Your edited note · not independently verified',{exact:true}).waitFor();
    await learning.getByText('Biology source',{exact:true}).click();
    await learning.getByRole('button',{name:'Confident',exact:true}).click();
    await learning.getByRole('button',{name:'Retry saving assessment',exact:true}).click();
    await learning.getByText('Assessment saved.',{exact:true}).waitFor();
    assert.equal(reviewAttempts.length,2);assert.deepEqual(reviewAttempts[0],reviewAttempts[1]);
    assert.equal(await learning.getByLabel('Practice answer (optional)').inputValue(),'My recall attempt');
    await learning.getByLabel('Practice focus').selectOption('review');
    await learning.getByText('No topics match this focus. Choose All topics or clear the search.',{exact:true}).waitFor();
    await learning.getByLabel('Practice focus').selectOption('all');
    await learning.getByRole('button',{name:'Refresh practice',exact:true}).click();
    await learning.getByText('1 of 1 topics self-rated confident.',{exact:true}).waitFor();
    await learning.getByRole('button',{name:'Reveal saved answer',exact:true}).click();
    conflictReview=true;
    await learning.getByRole('button',{name:'Needs review',exact:true}).click();
    await learning.getByRole('alert').filter({hasText:'changed in another window'}).waitFor();
    assert.ok(await learning.getByRole('button',{name:'Confident',exact:true}).isDisabled());
    await learning.getByRole('button',{name:'Refresh practice',exact:true}).click();
    await learning.getByRole('button',{name:'Reveal saved answer',exact:true}).click();
    await learning.getByRole('button',{name:'Reset assessment',exact:true}).click();
    await learning.getByText('0 of 1 topics self-rated confident.',{exact:true}).waitFor();
    await mkdir('.local/study-review',{recursive:true});await page.screenshot({path:'.local/study-review/midnight.png',fullPage:true});
    await page.setViewportSize({width:400,height:850});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'.local/study-review/narrow.png',fullPage:true});assert.deepEqual(errors,[]);
    console.log('Study UI passed: markers, catch-up, glossary conflicts, recall/reveal, cited answers, assessment retry identity, persistence, focus filter, conflict recovery/reset, Midnight and narrow layout.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
