const test=require('node:test');
const assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');
const {requestMicrophone,restoreWindow,macMenu,bindPowerEvents,MICROPHONE_SETTINGS}=require('../../apps/desktop/mac-integration.cjs');
const {ORIGIN}=require('../../apps/desktop/policy.cjs');

test('Mac microphone requests deny other media and origins before touching OS permissions',async()=>{
  for(const [url,types] of [['https://example.com',['audio']],[ORIGIN,['video']],[ORIGIN,['audio','video']]]){
    assert.equal(await requestMicrophone({contents:{getURL:()=>url},permission:'media',details:{mediaTypes:types},platform:'darwin'}),false);
  }
});
test('Mac first request, denial recovery, restricted state and navigation are fail closed',async()=>{
  let status='not-determined',requests=0,dialogs=0,opened='',url=ORIGIN;
  const args={contents:{getURL:()=>url},permission:'media',details:{mediaTypes:['audio']},platform:'darwin',
    systemPreferences:{getMediaAccessStatus:()=>status,askForMediaAccess:async type=>{assert.equal(type,'microphone');requests++;status='denied';}},
    dialog:{showMessageBox:async()=>{dialogs++;return {response:1};}},shell:{openExternal:async value=>{opened=value;}}};
  assert.equal(await requestMicrophone(args),false);assert.equal(requests,1);assert.equal(opened,MICROPHONE_SETTINGS);
  assert.equal(await requestMicrophone(args),false);assert.equal(requests,1);
  status='restricted';assert.equal(await requestMicrophone(args),false);assert.equal(dialogs,3);
  status='granted';assert.equal(await requestMicrophone(args),true);assert.equal(dialogs,3);
  status='not-determined';args.systemPreferences.askForMediaAccess=async()=>{status='granted';url='https://example.com';};
  assert.equal(await requestMicrophone(args),false);
});
test('Windows keeps its per-lecture permission confirmation',async()=>{
  let response=1;
  const args={contents:{getURL:()=>ORIGIN},permission:'media',details:{mediaTypes:['audio']},platform:'win32',dialog:{showMessageBox:async()=>({response})}};
  assert.equal(await requestMicrophone(args),false);response=0;assert.equal(await requestMicrophone(args),true);
});
test('Dock restores the same minimized workspace and Mac menu uses guarded Quit',()=>{
  const calls=[];
  restoreWindow({isDestroyed:()=>false,isMinimized:()=>true,restore:()=>calls.push('restore'),show:()=>calls.push('show'),focus:()=>calls.push('focus')});
  assert.deepEqual(calls,['restore','show','focus']);
  const menu=macMenu({quit:()=>calls.push('quit'),showSetup:()=>calls.push('setup')});
  menu[0].submenu.find(item=>item.accelerator==='Command+Q').click();
  menu[0].submenu.find(item=>item.accelerator==='Command+,').click();
  assert.deepEqual(calls.slice(-2),['quit','setup']);
  assert.equal(menu[2].role,'editMenu');
});
test('power event forwarding is bounded to known events and removable',()=>{
  const monitor=new EventEmitter(),events=[];
  const remove=bindPowerEvents(monitor,kind=>events.push(kind));
  monitor.emit('suspend');monitor.emit('resume');monitor.emit('lock-screen');
  remove();monitor.emit('suspend');assert.deepEqual(events,['suspend','resume']);
});
