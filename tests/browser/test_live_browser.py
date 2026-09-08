"""Run explicitly with Playwright installed; never requests microphone access.

PYTHONPATH=apps/api:apps/api/tests .venv/bin/python -m pytest -q tests/browser
Requires npm ci; starts its own loopback API and Next development server.
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
    # Refuse to touch another process already occupying our dedicated test ports.
    for port in (3000,8801):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            probe.bind(('127.0.0.1',port))
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8801,log_level='error'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    with (tmp_path/'web.log').open('w') as log:
        web=subprocess.Popen(['node',str(ROOT/'node_modules/next/dist/bin/next'),'dev','--hostname','127.0.0.1','--port','3000'],
            cwd=ROOT/'apps/web',env={**os.environ,'API_ORIGIN':'http://127.0.0.1:8801','NEXT_TELEMETRY_DISABLED':'1'},stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1',3000))==0 and server.started:break
                time.sleep(.1)
            else:pytest.fail('Test servers did not start')
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                context=browser.new_context(viewport={'width':1440,'height':1000})
                context.add_cookies([{'name':'nt_session','value':client.cookies.get('nt_session'),
                    'domain':'127.0.0.1','path':'/','httpOnly':True,'sameSite':'Strict'}])
                check=context.request.get('http://127.0.0.1:3000/api/session')
                assert check.status==200, (check.status,check.text())
                page=context.new_page();errors=[]
                page.add_init_script("window.testSockets=[];const Native=WebSocket;window.WebSocket=class extends Native{constructor(...args){super(...args);window.testSockets.push(this)}}")
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:3000/#lecture/'+path.split('/')[-1])
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
                screenshots=ROOT/'.local';screenshots.mkdir(exist_ok=True)
                page.screenshot(path=str(screenshots/'m05-browser-desktop.png'),full_page=True)
                # Layout stays usable on narrow windows too.
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(screenshots/'m05-browser-mobile.png'),full_page=True)
                browser.close()
        finally:
            server.should_exit=True;thread.join(timeout=5)
            web.terminate()
            try:web.wait(timeout=5)
            except subprocess.TimeoutExpired:web.kill();web.wait(timeout=5)
