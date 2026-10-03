// Actual React workspace with synthetic responses; no microphone, lecture data, or provider calls.
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const {mkdir}=require('node:fs/promises');
const root=path.resolve(__dirname,'../..');
const playwrightDriver=process.env.PLAYWRIGHT_DRIVER||(process.platform==='win32'?path.resolve(root,'.venv/Lib/site-packages/playwright/driver/package'):
  execFileSync('uv',['run','--no-project','--with','playwright==1.55.0','python','-c','import pathlib, playwright; print(pathlib.Path(playwright.__file__).parent / "driver" / "package")'],{cwd:root,encoding:'utf8'}).trim());
const {chromium}=require(playwrightDriver);

function contrastRatio(foreground,background){
  const luminance=color=>{
    const rgb=color.match(/[\d.]+/g).slice(0,3).map(Number).map(value=>{
      value/=255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;
    });
    return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
  };
  const a=luminance(foreground),b=luminance(background);
  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}

(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>{
      navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Microphone forbidden');};
      window.desktopApp={platform:'win32',appearance:async theme=>{window.lastAppearance=theme;},openSetup:async()=>{window.setupOpened=(window.setupOpened||0)+1;}};
    });
    await page.route('**/api/**',async route=>{
      const path=new URL(route.request().url()).pathname;
      const body=path==='/api/session/open'?{owner_id:'synthetic-settings',csrf_token:'test-csrf',preview:true}:
        path==='/api/courses'?[]:path==='/api/deletions'?[]:path==='/api/provider-connections'?{connections:[]}:[];
      await route.fulfill({json:body});
    });
    await page.goto(process.env.NOTETAKER_UI_ORIGIN||'http://127.0.0.1:3016/');
    const trigger=page.getByRole('button',{name:'Settings',exact:true});
    await trigger.waitFor();
    assert.equal(await trigger.getAttribute('title'),'Settings');
    assert.match(await trigger.innerText(),/^\s*⚙\s*$/);
    await page.keyboard.press('Tab');
    const skipLink=page.getByRole('link',{name:'Skip to content',exact:true});
    assert.equal(await skipLink.evaluate(element=>document.activeElement===element),true,'Skip to content remains the first keyboard stop');
    await page.keyboard.press('Tab');
    assert.equal(await trigger.evaluate(element=>document.activeElement===element),true,'Settings trigger follows Skip to content in keyboard order');
    await page.keyboard.press('Enter');
    const settings=page.getByRole('dialog',{name:'Settings'});
    await settings.waitFor();
    assert.equal(await settings.getByRole('heading',{name:'Settings',exact:true}).count(),1);
    assert.equal(await page.evaluate(()=>document.activeElement?.textContent?.trim()),'Close','dialog moves focus to its close control');
    await page.keyboard.press('Escape');
    await settings.waitFor({state:'hidden'});
    assert.equal(await trigger.evaluate(element=>document.activeElement===element),true,'Escape returns focus to Settings');

    await trigger.click();
    await settings.waitFor();
    await settings.getByRole('button',{name:'Accounts & API keys'}).click();
    const accounts=page.getByRole('dialog',{name:'Accounts & API keys'});
    await accounts.waitFor();
    await accounts.getByRole('button',{name:'Close',exact:true}).click();
    await accounts.waitFor({state:'hidden'});
    assert.equal(await settings.getByRole('button',{name:'Accounts & API keys'}).evaluate(element=>document.activeElement===element),true,'nested account dialog returns focus to its Settings action');
    await settings.getByRole('button',{name:'Workspace setup'}).click();
    assert.equal(await page.evaluate(()=>window.setupOpened),1,'workspace setup remains reachable from Settings');
    assert.equal(await settings.getByText('No data removal is in progress.').count(),1);

    await mkdir('.local/settings-review',{recursive:true});
    for(const theme of ['light','dark','pink','blue']){
      await settings.getByLabel('App theme').selectOption(theme);
      await page.waitForFunction(value=>document.documentElement.dataset.theme===value,theme);
      assert.equal(await page.evaluate(()=>localStorage.getItem('notetaker:theme')),theme,`${theme} preference persists`);
      await page.keyboard.press('Tab');await page.keyboard.press('Shift+Tab');
      const measurements=await settings.evaluate(dialog=>{
        const background=element=>{
          let current=element;
          while(current){
            const color=getComputedStyle(current).backgroundColor;
            if(color!=='rgba(0, 0, 0, 0)'&&color!=='transparent')return color;
            current=current.parentElement;
          }
          return getComputedStyle(document.documentElement).backgroundColor;
        };
        const pairs=[
          ['title',dialog.querySelector('#settings-title')],
          ['dialog description',dialog.querySelector('.settings-heading .muted')],
          ['theme label',dialog.querySelector('label[for="app-theme"]')],
          ['theme select',dialog.querySelector('#app-theme')],
          ['workspace action',dialog.querySelector('.settings-action')],
          ['data status',dialog.querySelector('.removal-empty')],
        ].map(([name,element])=>({name,color:getComputedStyle(element).color,background:background(element)}));
        const select=dialog.querySelector('#app-theme'),style=getComputedStyle(select);
        return {pairs,border:style.borderTopColor,controlBackground:style.backgroundColor,focus:style.outlineColor,surface:getComputedStyle(dialog).backgroundColor};
      });
      const textContrasts=measurements.pairs.map(pair=>contrastRatio(pair.color,pair.background));
      for(const [index,pair] of measurements.pairs.entries()){
        const ratio=textContrasts[index];
        assert.ok(ratio>=4.5,`${theme} ${pair.name} contrast ${ratio.toFixed(2)}:1 (${pair.color} on ${pair.background})`);
      }
      const selectorContrast=contrastRatio(measurements.border,measurements.controlBackground);
      const focusContrast=contrastRatio(measurements.focus,measurements.surface);
      assert.ok(selectorContrast>=3,`${theme} theme selector boundary contrast ${selectorContrast.toFixed(2)}:1`);
      assert.ok(focusContrast>=3,`${theme} focus color contrast ${focusContrast.toFixed(2)}:1`);
      await settings.getByLabel('App theme').focus();
      const focusStyle=await settings.getByLabel('App theme').evaluate(element=>({style:getComputedStyle(element).outlineStyle,width:getComputedStyle(element).outlineWidth}));
      assert.equal(focusStyle.style,'solid');assert.notEqual(focusStyle.width,'0px');
      await page.screenshot({path:`.local/settings-review/${theme}.png`,fullPage:true});
      console.log(`${theme}: minimum Settings text ${Math.min(...textContrasts).toFixed(2)}:1; selector boundary ${selectorContrast.toFixed(2)}:1; focus ${focusContrast.toFixed(2)}:1`);
    }
    await page.getByLabel('App theme').selectOption('pink');
    await page.getByRole('button',{name:'Close',exact:true}).click();
    await settings.waitFor({state:'hidden'});
    assert.equal(await trigger.evaluate(element=>document.activeElement===element),true,'Close returns focus to Settings');
    await page.reload();
    await trigger.waitFor();
    assert.equal(await page.locator('html').getAttribute('data-theme'),'pink','theme survives reload');
    await trigger.click();await settings.waitFor();
    assert.equal(await settings.getByLabel('App theme').inputValue(),'pink','saved theme is selected in Settings');
    await page.setViewportSize({width:360,height:740});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'narrow layout fits without horizontal page scroll');
    assert.equal(await settings.evaluate(dialog=>dialog.getBoundingClientRect().width<=innerWidth),true,'Settings dialog fits narrow screen');
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),true);
    assert.ok(await trigger.evaluate(element=>parseFloat(getComputedStyle(element).transitionDuration)<=.001),'reduced motion reduces Settings trigger transition below 1ms');
    const scroll=await page.evaluate(()=>({width:getComputedStyle(document.body,'::-webkit-scrollbar').width,thumb:getComputedStyle(document.body,'::-webkit-scrollbar-thumb').backgroundColor}));
    assert.equal(scroll.width,'10px');assert.notEqual(scroll.thumb,'rgba(0, 0, 0, 0)');
    assert.deepEqual(errors,[]);
    console.log('Settings keyboard open/Escape/close, focus restoration, nested accounts, persisted themes, four palette contrasts, 360px layout and reduced motion passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
