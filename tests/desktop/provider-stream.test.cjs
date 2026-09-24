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
