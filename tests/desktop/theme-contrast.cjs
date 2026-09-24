// Synthetic rendering of the affected nested workspace surfaces; no user data.
const {chromium}=require('../../.venv/Lib/site-packages/playwright/driver/package');
const {readFile,mkdir}=require('node:fs/promises');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1050,height:900}});
    const css=(await readFile('apps/web/app/globals.css','utf8'))+(await readFile('apps/web/app/themes.css','utf8'));
    await page.setContent(`<style>${css}</style><main style="padding:24px"><h1>Your lecture workspace</h1><nav class="lecture-tabs"><button class="active">Study notes</button><button>Transcript</button><button>Materials</button></nav><section class="materials-panel"><h2>Course materials</h2><div class="materials-guidance"><p><strong>What gets read</strong> Text from your course files.</p></div><div class="materials-uploader"><div class="materials-step"><span class="materials-step-number">1</span><div class="materials-step-body"><label>Choose the source type</label><select><option>Syllabus</option></select></div></div><div class="materials-step"><span class="materials-step-number">2</span><div class="materials-step-body"><label>Choose a file</label><input type="file"><div class="materials-empty-file">No file selected yet</div></div></div><div class="materials-actions"><button class="primary">Save material</button></div></div><div class="materials-library-empty"><p>No files saved yet.</p>Add a syllabus or slide deck above.</div></section><aside class="note-controls"><div class="model-picker-status">4 models available</div><select><option>Your note model</option></select><label class="cloud-consent">I understand this sends the selected transcript and prompts to the provider.</label><details class="provider-connections" open><summary>Accounts and API keys</summary><input placeholder="API key"></details></aside></main>`);
    await mkdir('.local/theme-review',{recursive:true});
    for(const theme of ['light','dark','pink','blue']){
      await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
      const contrasts=await page.evaluate(()=>{
        const luminance=color=>{const rgb=color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
        return ['.materials-guidance','.materials-step-body label','.materials-empty-file','.materials-library-empty p','.note-controls select','.cloud-consent','.provider-connections summary','.model-picker-status'].map(selector=>{
          const element=document.querySelector(selector);let parent=element,bg;
          while(parent){bg=getComputedStyle(parent).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)')break;parent=parent.parentElement;}
          const a=luminance(getComputedStyle(element).color),b=luminance(bg);return {selector,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
        });
      });
      for(const row of contrasts)assert.ok(row.ratio>=4.5,`${theme} ${row.selector}: ${row.ratio}`);
      await page.screenshot({path:`.local/theme-review/${theme}.png`,fullPage:true});
      console.log(`${theme}: ${contrasts.length} affected text/surface pairs pass 4.5:1 contrast`);
    }
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
