const test=require('node:test');
const assert=require('node:assert/strict');
const {readProviderStream}=require('../../apps/desktop/provider-stream.cjs');
const frame=value=>'data: '+JSON.stringify(value)+'\r\n\r\n';

test('OpenAI text is forwarded before completion across byte and Unicode boundaries',async()=>{
  let release;
  const gate=new Promise(resolve=>release=resolve),previews=[];
  const bytes=new TextEncoder().encode(frame({choices:[{delta:{content:'{"text":"α'}}]}));
  const body=new ReadableStream({async start(controller){
    for(const byte of bytes)controller.enqueue(Uint8Array.of(byte));
    await gate;
    controller.enqueue(new TextEncoder().encode(frame({choices:[{delta:{content:'"}'},finish_reason:'stop'}]})));
    controller.close();
  }});
  const result=readProviderStream(new Response(body),'openai',text=>{previews.push(text);release();});
  assert.equal((await result).raw,'{"text":"α"}');
  assert.equal(previews[0],'{"text":"α');
});

test('Anthropic incremental text and usage are retained; interrupted and tool streams fail',async()=>{
  const previews=[];
  const response=new Response(frame({type:'content_block_delta',delta:{text:'hello'}})+frame({type:'message_delta',delta:{stop_reason:'end_turn'},usage:{output_tokens:1}}));
  assert.deepEqual(await readProviderStream(response,'anthropic',text=>previews.push(text)),{raw:'hello',metrics:{output_tokens:1}});
  assert.deepEqual(previews,['hello']);
  await assert.rejects(readProviderStream(new Response(frame({choices:[{delta:{content:'partial'}}]})),'openai'),/Incomplete/);
  await assert.rejects(readProviderStream(new Response(frame({type:'content_block_start',content_block:{type:'tool_use'}})),'anthropic'),/tool/);
  await assert.rejects(readProviderStream(new Response(frame({choices:[{delta:{content:'partial'},finish_reason:'length'}]})),'openai'),/Incomplete/);
});

test('Ollama Cloud NDJSON forwards content across boundaries and never exposes thinking',async()=>{
  const lines=[{message:{role:'assistant',content:'',thinking:'private reasoning'},done:false},
    {message:{role:'assistant',content:'{"text":"β'},done:false},
    {message:{role:'assistant',content:'"}'},done:true,done_reason:'stop',eval_count:7,prompt_eval_count:11}];
  const bytes=new TextEncoder().encode(lines.map(line=>JSON.stringify(line)).join('\n')+'\n');
  const body=new ReadableStream({start(controller){for(const byte of bytes)controller.enqueue(Uint8Array.of(byte));controller.close();}});
  const previews=[];
  const result=await readProviderStream(new Response(body),'ollama-cloud',text=>previews.push(text));
  assert.deepEqual(result,{raw:'{"text":"β"}',metrics:{prompt_eval_count:11,eval_count:7}});
  assert.equal(previews.some(text=>text.includes('private reasoning')),false);
  const ndjson=(...values)=>new Response(values.map(value=>JSON.stringify(value)).join('\n'));
  await assert.rejects(readProviderStream(ndjson({message:{content:'partial'},done:true,done_reason:'length'}),'ollama-cloud'),/Incomplete/);
  await assert.rejects(readProviderStream(ndjson({message:{content:'partial'},done:false}),'ollama-cloud'),/Incomplete/);
  await assert.rejects(readProviderStream(ndjson({message:{tool_calls:[{function:{name:'x'}}]},done:false}),'ollama-cloud'),/tool/);
  await assert.rejects(readProviderStream(ndjson({error:'model not found'}),'ollama-cloud'),/failed/);
});
