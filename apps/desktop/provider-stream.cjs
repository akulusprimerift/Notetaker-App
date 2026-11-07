'use strict';

// Ollama's native chat API streams newline-delimited JSON. Only message content is
// note output; model reasoning in message.thinking is never previewed or returned.
async function readOllamaStream(response, onPreview) {
  let buffer='', raw='', metrics={}, complete=false;
  const decoder=new TextDecoder();
  const line=text=>{
    if(!text.trim())return;
    if(complete)throw new Error('Unexpected provider output after completion');
    const value=JSON.parse(text);
    if(!value||typeof value!=='object'||value.error)throw new Error('Provider stream failed');
    const message=value.message||{};
    if(message.tool_calls?.length)throw new Error('Unsupported tool request');
    const delta=message.content??'';
    if(typeof delta!=='string')throw new Error('Invalid provider text');
    raw+=delta;
    if(raw.length>2_000_000)throw new Error('Provider output too large');
    if(delta)onPreview?.(raw);
    if(value.done===true){
      if(value.done_reason!=='stop')throw new Error('Incomplete provider output');
      complete=true;
      for(const key of ['prompt_eval_count','eval_count','total_duration'])if(typeof value[key]==='number')metrics[key]=value[key];
    }
  };
  for await(const chunk of response.body){
    buffer+=decoder.decode(chunk,{stream:true});
    let boundary;
    while((boundary=buffer.indexOf('\n'))>=0){line(buffer.slice(0,boundary));buffer=buffer.slice(boundary+1);}
    if(buffer.length>2_000_000)throw new Error('Provider frame too large');
  }
  buffer+=decoder.decode();
  line(buffer);
  if(!complete||!raw)throw new Error('Incomplete provider stream');
  return {raw,metrics};
}

// Decode SSE across arbitrary UTF-8/network boundaries. Never expose provider
// metadata or JSON scaffolding as note prose; the API extracts that separately.
async function readProviderStream(response, provider, onPreview) {
  if(provider==='ollama-cloud')return readOllamaStream(response,onPreview);
  let buffer='', raw='', metrics={}, complete=false;
  const decoder=new TextDecoder();
  const event=frame=>{
    const data=frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
    if(!data||data==='[DONE]')return;
    const value=JSON.parse(data);
    if(value.error||value.type==='error')throw new Error('Provider stream failed');
    let delta='';
    if(provider==='openai'){
      const choice=value.choices?.[0];
      if(choice?.delta?.tool_calls)throw new Error('Unsupported tool request');
      delta=choice?.delta?.content||'';
      if(choice?.finish_reason){if(choice.finish_reason!=='stop')throw new Error('Incomplete provider output');complete=true;}
      if(value.usage)metrics=value.usage;
    }else{
      if(value.type==='content_block_start'){
        if(value.content_block?.type==='tool_use')throw new Error('Unsupported tool request');
        delta=value.content_block?.text||'';
      }
      if(value.type==='content_block_delta')delta=value.delta?.text||'';
      if(value.type==='message_delta'){
        if(value.delta?.stop_reason&&value.delta.stop_reason!=='end_turn')throw new Error('Incomplete provider output');
        if(value.delta?.stop_reason==='end_turn')complete=true;
      }
      if(value.usage)metrics={...metrics,...value.usage};
    }
    if(typeof delta!=='string')throw new Error('Invalid provider text');
    raw+=delta;
    if(raw.length>2_000_000)throw new Error('Provider output too large');
    if(delta)onPreview?.(raw);
  };
  for await(const chunk of response.body){
    buffer+=decoder.decode(chunk,{stream:true});
    buffer=buffer.replace(/\r\n/g,'\n');
    let boundary;
    while((boundary=buffer.indexOf('\n\n'))>=0){event(buffer.slice(0,boundary));buffer=buffer.slice(boundary+2);}
    if(buffer.length>2_000_000)throw new Error('Provider frame too large');
  }
  buffer+=decoder.decode();
  if(buffer.trim())event(buffer);
  if(!complete||!raw)throw new Error('Incomplete provider stream');
  return {raw,metrics};
}
module.exports={readProviderStream};
