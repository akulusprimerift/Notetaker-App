"""Run explicitly with Playwright installed; never requests microphone access.

PYTHONPATH=apps/api:apps/api/tests .venv/bin/python -m pytest -q tests/browser
Requires bun install --frozen-lockfile; starts its own loopback API and Next development server.
"""
import os
import json
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
import httpx
from playwright.sync_api import sync_playwright, expect
from test_workspace import setup
from test_capture import capture
from test_live import enable, append
from test_notes import FakeNotes, correction
from notetaker.note_worker import plan, claim, execute

ROOT = Path(__file__).resolve().parents[2]


def test_custom_preferences_and_reconnect_preserve_reading(capture, tmp_path):
    app,client,headers,path,run = capture
    layer=app.middleware_stack
    while layer is not None:
        if hasattr(layer,'allowed_hosts'):layer.allowed_hosts.append('127.0.0.1')
        layer=getattr(layer,'app',None)
    enable(app,client,headers,path);append(*capture,0);plan(app.state.sessions)
    assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
    # Use independent loopback ports; the user's Docker preview may be running.
    ports=[]
    for _ in range(2):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));ports.append(probe.getsockname()[1])
    web_port,api_port=ports
    origin=f'http://127.0.0.1:{web_port}'
    app.state.settings.web_origin=origin
    headers['origin']=origin
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=api_port,log_level='error'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    with (tmp_path/'web.log').open('w') as log:
        web=subprocess.Popen(['node',str(ROOT/'node_modules/next/dist/bin/next'),'dev','--hostname','127.0.0.1','--port',str(web_port)],
            cwd=ROOT/'apps/web',env={**os.environ,'API_ORIGIN':f'http://127.0.0.1:{api_port}','NEXT_TELEMETRY_DISABLED':'1'},stdout=log,stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1',web_port))==0 and server.started:break
                time.sleep(.1)
            else:pytest.fail('Test servers did not start')
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                context=browser.new_context(viewport={'width':1440,'height':1000})
                context.add_cookies([{'name':'nt_session','value':client.cookies.get('nt_session'),
                    'domain':'127.0.0.1','path':'/','httpOnly':True,'sameSite':'Strict'}])
                check=context.request.get(origin+'/api/session')
                assert check.status==200, (check.status,check.text())
                for stream_origin in (f'http://127.0.0.1:{api_port}',origin+'/api'):
                    with httpx.stream('GET',stream_origin+path+'/notes/stream',
                            cookies={'nt_session':client.cookies.get('nt_session')},timeout=4,trust_env=False) as response:
                        assert response.status_code==200, (stream_origin,response.status_code)
                        assert response.headers.get('content-encoding')!='gzip'
                        first=next(response.iter_lines())
                        assert first.startswith('data: '),(stream_origin,first)
                page=context.new_page();errors=[]
                page.add_init_script("window.testSockets=[];const Native=WebSocket;window.WebSocket=class extends Native{constructor(...args){super(...args);window.testSockets.push(this)}}")
                page.add_init_script("window.streamEvents=[];const Source=EventSource;window.EventSource=class extends Source{constructor(...args){super(...args);this.addEventListener('message',e=>window.streamEvents.push(e.data));this.addEventListener('error',()=>window.streamEvents.push('stream error'))}}")
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(origin+'/#lecture/'+path.split('/')[-1])
                expect(page.get_by_text('Live updates connected',exact=True)).to_be_visible(timeout=30000)
                detail=page.get_by_label('Describe your detail level (optional)')
                layout=page.get_by_label('Describe your layout (optional)')
                detail.fill('Explain all worked examples step by step.')
                layout.fill('Use a concept heading, explanation, example, then review question.')
                page.get_by_role('button',name='Apply note preferences').click()
                expect(page.get_by_role('button',name='Apply note preferences')).to_be_disabled()
                profile=client.get(path+'/notes').json()['profile']
                assert profile['detail_prompt']=='Explain all worked examples step by step.'
                assert profile['layout_prompt'].startswith('Use a concept heading')
                plan(app.state.sessions)
                assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
                expect(page.get_by_role('button',name='Show updated notes (revision 2)')).to_be_visible(timeout=10000)
                page.get_by_role('button',name='Show updated notes (revision 2)').click()
                # Keep a focused unsaved preference and a selected piece of lecture text.
                detail.fill('Keep this unsaved preference through reconnect.')
                source=page.locator('.study-text').first
                source.scroll_into_view_if_needed()
                source.evaluate('el=>{const range=document.createRange();range.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(range)}')
                selected=page.evaluate('getSelection().toString()')
                scroll=page.evaluate('scrollY')
                context.set_offline(True)
                page.evaluate("window.testSockets.filter(s=>s.url.includes('/updates')).forEach(s=>s.close())")
                append(*capture,1);plan(app.state.sessions)
                assert execute(app.state.sessions,FakeNotes(),claim(app.state.sessions),heartbeat=False)
                context.set_offline(False)
                expect(page.get_by_role('button',name='Show updated notes (revision 3)')).to_be_visible(timeout=20000)
                expect(page.get_by_text('Live updates connected',exact=True)).to_be_visible(timeout=20000)
                assert page.evaluate('getSelection().toString()')==selected
                assert abs(page.evaluate('scrollY')-scroll)<120
                assert detail.input_value()=='Keep this unsaved preference through reconnect.'
                assert page.locator('.note-revision').inner_text().startswith('Revision 2')
                assert not errors,errors
                # A snapshot reset may move the cursor backwards after restored history.
                restored=client.get(path+'/snapshot').json()
                restored['update_cursor']=0
                restored['transcript']['status']='needs_attention'
                pattern='**/api'+path+'/snapshot'
                page.route(pattern,lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(restored)))
                page.evaluate("window.testSockets.filter(s=>s.url.includes('/updates')&&s.readyState===1).forEach(s=>s.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({schema_version:1,kind:'snapshot_required',cursor:0})})))")
                expect(page.locator('.transcript-status')).to_contain_text('Transcription needs attention',timeout=10000)
                page.unroute(pattern)
                expect(page.locator('.transcript-status')).to_contain_text('Listening',timeout=10000)
                transcript=page.locator('.passage-text').first
                transcript.scroll_into_view_if_needed()
                transcript.evaluate('el=>{const r=document.createRange();r.selectNodeContents(el);getSelection().removeAllRanges();getSelection().addRange(r)}')
                selected_transcript=page.evaluate('getSelection().toString()')
                correction(client,headers,path,'Binary search requires sorted input; this is a corrected revision.')
                expect(page.get_by_role('button',name='Show transcript revisions')).to_be_visible(timeout=10000)
                assert page.evaluate('getSelection().toString()')==selected_transcript
                page.get_by_role('button',name='Show transcript revisions').click()
                expect(page.locator('.passage-text').first).to_have_text('Binary search requires sorted input; this is a corrected revision.')
                assert page.locator('#note-depth').count()==0 and page.locator('#note-format').count()==0
                page.get_by_role('button',name='Show updated notes (revision 3)').click()
                page.get_by_role('button',name='Edit notes',exact=True).click()
                expect(page.locator('.note-draft')).to_be_visible()
                assert not errors,errors
                page.get_by_label('Passage 1',exact=True).fill('My protected explanation.\n    lo = mid + 1\nE = mc²')
                expect(page.get_by_text('Draft saved on this device. Export uses the saved revision.',exact=True)).to_be_visible()
                page.reload()
                expect(page.get_by_role('button',name='Restore draft from')).to_be_visible(timeout=20000)
                page.get_by_role('button',name='Restore draft from').first.click()
                expect(page.get_by_label('Passage 1',exact=True)).to_have_value('My protected explanation.\n    lo = mid + 1\nE = mc²')
                page.get_by_label('Upload material', exact=True).set_input_files({'name':'Course-outline.txt','mimeType':'text/plain','buffer':b'Binary search: sorted input, logarithmic comparisons.'})
                expect(page.get_by_text('Material saved.', exact=False)).to_be_visible(timeout=10000)
                page.get_by_text('Course-outline.txt · syllabus', exact=False).click()
                expect(page.get_by_text('Binary search: sorted input, logarithmic comparisons.', exact=True)).to_be_visible()
                # Hold the provider open until the real SSE browser receives partial text.
                release=threading.Event()
                class Streaming(FakeNotes):
                    def generate_stream(self,evidence,pref,preview):
                        preview('A streamed explanation appears before generation finishes.')
                        assert release.wait(25), 'Browser did not observe streaming output'
                        return self.generate(evidence,pref)
                plan(app.state.sessions)
                chosen_job=claim(app.state.sessions)
                outcomes=[]
                generation=threading.Thread(target=lambda:outcomes.append(execute(app.state.sessions,Streaming(),chosen_job,heartbeat=False)))
                generation.start()
                try:
                    try:
                        expect(page.locator('.streaming-text')).to_contain_text('A streamed explanation appears before generation finishes.',timeout=15000)
                    except AssertionError:
                        pytest.fail('Stream events: '+str(page.evaluate('window.streamEvents'))+'; worker results: '+str(outcomes))
                    assert client.get(path+'/notes').json()['status']=='generating'
                    page.get_by_role('button',name='Save my changes').click()
                    expect(page.locator('.note-revision')).to_contain_text('Student revision 1')
                finally:
                    release.set();generation.join(timeout=10)
                assert outcomes==[True]
                expect(page.get_by_role('button',name='Compare suggestion')).to_be_visible(timeout=15000)
                page.get_by_role('button',name='Compare suggestion').click()
                expect(page.locator('.note-comparison')).to_contain_text('My protected explanation.')
                page.locator('.note-comparison input[type=checkbox]').first.check()
                page.get_by_role('button',name='Merge selected sections').click()
                expect(page.locator('.note-revision')).to_contain_text('Student revision 2')
                expect(page.locator('.generated-content')).to_contain_text('My protected explanation.')
                page.get_by_role('button',name='Revision history and undo').click()
                page.get_by_role('button',name='Restore student revision 1 (save)',exact=True).click()
                expect(page.locator('.note-revision')).to_contain_text('Student revision 3')
                assert client.get(path+'/notes').json()['editing']['selected']['content']['blocks'][0]['passages'][0]['text'].startswith('My protected explanation.')
                assert not errors,errors
                # M07 entry: profiles persist every prompt and load without applying.
                detail.fill('Preserve each worked example.')
                layout.fill('Organize by concept.')
                page.get_by_label('Writing preferences (optional)').fill('Explain unfamiliar terms.')
                page.get_by_label('Profile name',exact=True).fill('Study profile')
                page.get_by_role('button',name='Save prompts as new profile').click()
                expect(page.get_by_text('Profile saved. You can use it in any lecture.',exact=True)).to_be_visible()
                page.reload()
                page.get_by_label('Saved profile',exact=True).select_option(label='Study profile')
                page.get_by_role('button',name='Load profile prompts').click()
                expect(page.get_by_label('Describe your detail level (optional)')).to_have_value('Preserve each worked example.')
                expect(page.get_by_label('Writing preferences (optional)')).to_have_value('Explain unfamiliar terms.')
                assert page.get_by_label('Workspace code',exact=True).count()==0
                # A separate browser starts with no cookie/code and opens the same local owner.
                other_context=browser.new_context()
                other=other_context.new_page();other.goto(origin+'/#lecture/'+path.split('/')[-1])
                expect(other.get_by_role('heading',name='Your lecture notes',exact=True)).to_be_visible(timeout=30000)
                other.get_by_role('button',name='Edit notes',exact=True).click()
                other.get_by_label('Passage 1',exact=True).fill('A disconnected draft must be purged on reconnect.')
                expect(other.get_by_text('Draft saved on this device. Export uses the saved revision.',exact=True)).to_be_visible()
                other_context.set_offline(True)
                page.get_by_role('button',name='Finalize available results now',exact=True).click()
                page.get_by_role('button',name='Confirm',exact=True).click()
                expect(page.get_by_text('Final snapshot saved with incomplete results',exact=True).first).to_be_visible(timeout=15000)
                page.get_by_text('Final snapshot history',exact=False).click()
                page.get_by_role('button',name='Read snapshot',exact=True).click()
                expect(page.get_by_role('region',name='Saved final snapshot')).to_contain_text('My protected explanation.')
                page.get_by_role('region',name='Finalization and data control').screenshot(path=str(ROOT/'.local/m07-finalization.png'))
                page.get_by_role('button',name='Close snapshot',exact=True).click()
                page.get_by_role('button',name='Remove audio',exact=True).click()
                page.get_by_role('button',name='Confirm',exact=True).click()
                expect(page.get_by_text('Audio removal · Server cleanup complete',exact=True)).to_be_visible(timeout=20000)
                expect(page.locator('.generated-content')).to_contain_text('My protected explanation.')
                page.get_by_role('button',name='Delete lecture',exact=True).click()
                page.get_by_role('button',name='Confirm',exact=True).click()
                expect(page.get_by_text('Lecture deletion · Server cleanup complete',exact=True)).to_be_visible(timeout=20000)
                assert client.get(path+'/notes').status_code==404
                # Offline browser keeps its local data until reconnection, then purges
                # durable drafts and unmounts its obsolete reading copy.
                assert other.evaluate("() => new Promise(resolve=>{const r=indexedDB.open('notetaker-note-drafts',2);r.onsuccess=()=>{const db=r.result;const q=db.transaction('drafts').objectStore('drafts').getAll();q.onsuccess=()=>{resolve(q.result.length);db.close()}}})")>0
                other_context.set_offline(False)
                expect(other.get_by_role('heading',name='Your lecture library.',exact=True)).to_be_visible(timeout=20000)
                expect(other.get_by_text('Copies in this browser have been removed.',exact=False).first).to_be_visible(timeout=15000)
                assert other.evaluate("() => new Promise(resolve=>{const r=indexedDB.open('notetaker-note-drafts',2);r.onsuccess=()=>{const db=r.result;const q=db.transaction('drafts').objectStore('drafts').getAll();q.onsuccess=()=>{resolve(q.result.length);db.close()}}})")==0
                other_context.close()
                assert not errors,errors
                screenshots=ROOT/'.local';screenshots.mkdir(exist_ok=True)
                page.screenshot(path=str(screenshots/'m07-browser-desktop.png'),full_page=True)
                # Layout stays usable on narrow windows too.
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(screenshots/'m07-browser-mobile.png'),full_page=True)
                browser.close()
        finally:
            server.should_exit=True;thread.join(timeout=5)
            if os.name=='nt' and web.poll() is None:
                subprocess.run(['taskkill','/PID',str(web.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
            else: web.terminate()
            try:web.wait(timeout=5)
            except subprocess.TimeoutExpired:web.kill();web.wait(timeout=5)
