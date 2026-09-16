// Actual React workspace with synthetic API responses; no accounts or microphone.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
const {mkdir}=require('node:fs/promises');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1200,height:1000}});
    let rows=[{provider:'claude-subscription',name:'claude-subscription/legacy-test',digest:'legacy'}],linked=false,saved=false,refreshed=false;
    const disconnected=[];
    await page.route('**/api/**',async route=>{
      const request=route.request(),url=new URL(request.url());let body=[];
      if(url.pathname==='/api/session/open')body={owner_id:'synthetic-owner',csrf_token:'test-csrf',preview:true};
      else if(url.pathname==='/api/courses')body=[{id:'synthetic-course',name:'Biology',code:'BIO 101',created_at:'2026-09-15T12:00:00Z'}];
      else if(url.pathname.endsWith('/terminology'))body={version:0,terms:[]};
      else if(url.pathname==='/api/provider-connections/chatgpt/sign-in'){
        assert.equal(request.headers()['x-csrf-token'],'test-csrf');assert.ok(request.headers()['idempotency-key']);
        assert.deepEqual(request.postDataJSON(),{});linked=true;rows.push({provider:'chatgpt',name:'chatgpt/gpt-test',digest:'test'});body={connections:rows};
      }else if(url.pathname==='/api/provider-connections/chatgpt/refresh'){
        refreshed=true;rows.push({provider:'chatgpt',name:'chatgpt/extra-model',digest:'test'});body={connections:rows};
      }else if(url.pathname.endsWith('/sign-out')){
        const provider=url.pathname.split('/').at(-2);disconnected.push(provider);rows=rows.filter(row=>row.provider!==provider);
        body={notice:'Disconnected from Notetaker. Client sign-out could not be confirmed.'};
      }else if(url.pathname==='/api/provider-connections'){
        if(request.method()==='POST'){
          assert.deepEqual(request.postDataJSON(),{provider:'openai',api_key:'synthetic-key'});saved=true;
          rows.push({provider:'openai',name:'openai/gpt-test',digest:'test-api'});
        }
        body={connections:rows};
      }
      await route.fulfill({json:body});
    });
    await page.goto(process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015');
    await page.getByRole('heading',{name:'Your lecture library.'}).waitFor();
    await page.getByLabel('App theme').selectOption('dark');
    const opener=page.getByRole('button',{name:'Accounts & API keys',exact:true});
    await opener.click();
    const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.equal(await dialog.getByText('Choose client',{exact:true}).count(),0);
    assert.equal(await dialog.getByText('Model ID',{exact:true}).count(),0);
    await dialog.getByRole('button',{name:'Link ChatGPT',exact:true}).click();
    await dialog.getByRole('button',{name:'ChatGPT linked',exact:true}).waitFor();assert.ok(linked);
    await dialog.getByRole('button',{name:'Refresh models',exact:true}).click();
    await dialog.getByText('2 model choices',{exact:true}).click();await dialog.getByText('extra-model',{exact:true}).waitFor();assert.ok(refreshed);
    await dialog.getByRole('button',{name:'Disconnect ChatGPT',exact:true}).click();await dialog.getByRole('button',{name:'Link ChatGPT',exact:true}).waitFor();
    await dialog.getByRole('button',{name:'Disconnect Claude subscription',exact:true}).click();await dialog.getByText('No accounts connected yet.',{exact:true}).waitFor();
    assert.deepEqual(disconnected,['chatgpt','claude-subscription']);
    await dialog.getByLabel('API key',{exact:true}).fill('synthetic-key');
    await dialog.getByRole('button',{name:'Connect API key',exact:true}).click();
    await dialog.getByRole('button',{name:'Disconnect OpenAI API',exact:true}).waitFor();assert.ok(saved);
    assert.equal(await dialog.getByLabel('API key',{exact:true}).inputValue(),'');
    await mkdir('.local/accounts-review',{recursive:true});
    await page.screenshot({path:'.local/accounts-review/midnight.png'});
    await page.keyboard.press('Escape');assert.equal(await dialog.isVisible(),false);
    assert.equal(await opener.evaluate(element=>element===document.activeElement),true);
    await page.setViewportSize({width:400,height:850});await opener.click();
    assert.ok(await dialog.evaluate(element=>element.scrollWidth<=element.clientWidth));
    await page.screenshot({path:'.local/accounts-review/narrow.png'});
    await page.keyboard.press('Escape');await page.setViewportSize({width:1200,height:1000});
    await page.goto((process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3015')+'/#course/synthetic-course');
    await page.locator('.materials-uploader').waitFor();
    assert.equal(await page.locator('.materials-uploader').evaluate(element=>getComputedStyle(element).backgroundColor),'rgb(18, 27, 45)');
    await page.screenshot({path:'.local/accounts-review/materials-midnight.png',fullPage:true});
    console.log('Accounts UI: browser-link request, key-only setup, secret clearing, keyboard focus restoration and narrow layout passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
