"""Official client bridges. Authentication stays with each provider's client."""
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
from .note_provider import NoteFailure, preview_text

CODEX_DISABLED = ('shell_tool', 'unified_exec', 'code_mode', 'code_mode_host', 'view_image',
    'computer_use', 'browser_use', 'browser_use_external', 'browser_use_full_cdp_access', 'in_app_browser',
    'apps', 'plugins', 'plugin_sharing', 'remote_plugin', 'hooks', 'multi_agent', 'multi_agent_v2',
    'image_generation', 'artifact', 'skill_search', 'workspace_dependencies', 'memories', 'shell_snapshot')


def client_environment(provider, directory):
    # Never inherit API keys or alternate endpoints into a subscription request.
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith(
        ('OPENAI_', 'ANTHROPIC_', 'CLAUDE_', 'CODEX_', 'NOTETAKER_', 'AWS_', 'AZURE_', 'GOOGLE_'))}
    home = Path(directory) / (provider+'-client')
    home.mkdir(parents=True, exist_ok=True)
    if provider == 'chatgpt':
        env['CODEX_HOME'] = str(home)
    else:
        env['CLAUDE_CONFIG_DIR'] = str(home)
        env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
        env['DISABLE_AUTOUPDATER'] = '1'
    return env


class ClientProcess:
    def __init__(self, args, env, cwd, timeout=600):
        from .process_job import ProcessJob
        self.job = ProcessJob()
        self.process = None
        self.events = queue.Queue(maxsize=128)
        self.closed = threading.Event()
        self.deadline = time.monotonic()+timeout
        try:
            self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=env, cwd=cwd, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.job.assign(self.process)
        except Exception:
            self.close()
            raise NoteFailure('subscription_client_unavailable') from None
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()

    def put(self, value):
        while not self.closed.is_set():
            try:
                self.events.put(value, timeout=.1); return
            except queue.Full:
                continue

    def read(self):
        try:
            size = 0
            while not self.closed.is_set():
                line = self.process.stdout.readline(2_000_001)
                if not line: break
                size += len(line)
                if size > 2_000_000:
                    self.put(NoteFailure('invalid_output')); return
                self.put(line)
        except (OSError, ValueError):
            pass
        finally:
            self.put(None)

    def event(self):
        remaining = self.deadline-time.monotonic()
        if remaining <= 0: raise NoteFailure('provider_timeout')
        try:
            line = self.events.get(timeout=remaining)
        except queue.Empty:
            raise NoteFailure('provider_timeout') from None
        if isinstance(line, NoteFailure): raise line
        if line is None: raise NoteFailure('truncated_output')
        try: return json.loads(line)
        except ValueError: raise NoteFailure('subscription_client_unavailable') from None

    def send(self, value):
        self.process.stdin.write((json.dumps(value)+'\n').encode()); self.process.stdin.flush()

    def close(self):
        self.closed.set(); self.job.close()
        if self.process:
            if self.process.poll() is None: self.process.kill()
            self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream: stream.close()


def codex_args(executable):
    args = [executable, 'app-server']
    for name in CODEX_DISABLED:
        args.extend(['-c', 'features.'+name+'=false'])
    args.extend(['-c', 'web_search="disabled"', '-c', 'approval_policy="never"',
                 '-c', 'sandbox_mode="read-only"', '-c', 'cli_auth_credentials_store="keyring"',
                 '-c', 'history.persistence="none"', '-c', 'project_doc_max_bytes=0'])
    return args


def codex_generate(row, messages, directory, on_preview):
    env = client_environment('chatgpt', directory)
    with tempfile.TemporaryDirectory(prefix='notetaker-context-') as cwd:
        client = ClientProcess(codex_args(row['executable']), env, cwd)
        try:
            client.send({'id':1, 'method':'initialize', 'params':{'clientInfo':{
                'name':'notetaker', 'title':'Notetaker', 'version':'0.4.0'}}})
            text, final = '', ''
            while True:
                event = client.event()
                if event.get('error'): raise NoteFailure('subscription_client_unavailable')
                if 'method' in event and 'id' in event:
                    # No approvals, tool calls, or credential changes are granted by note generation.
                    client.send({'id':event['id'], 'error':{'code':-32601, 'message':'Not supported by note generation'}})
                    raise NoteFailure('unexpected_tool_request')
                if event.get('id') == 1:
                    client.send({'method':'initialized'})
                    client.send({'id':2, 'method':'account/read', 'params':{}})
                elif event.get('id') == 2:
                    account = event.get('result', {}).get('account') or {}
                    if account.get('type') != 'chatgpt': raise NoteFailure('provider_authentication')
                    client.send({'id':3, 'method':'thread/start', 'params':{
                        'model':row['model'], 'cwd':cwd, 'ephemeral':True, 'approvalPolicy':'never', 'sandbox':'read-only'}})
                elif event.get('id') == 3:
                    thread = event['result']['thread']['id']
                    client.send({'id':4, 'method':'turn/start', 'params':{'threadId':thread,
                        'input':[{'type':'text', 'text':'\n\n'.join(m['content'] for m in messages)}]}})
                elif event.get('method') == 'item/agentMessage/delta':
                    text += event['params']['delta']
                    if on_preview: on_preview(preview_text(text))
                elif event.get('method') == 'item/completed':
                    item = event['params']['item']
                    if item.get('type') == 'agentMessage': final = item.get('text', '')
                elif event.get('method') == 'turn/completed':
                    if event['params']['turn']['status'] != 'completed': raise NoteFailure('provider_limit_or_failure')
                    return final or text, {'client':'codex-app-server', 'billing':'subscription'}
        finally:
            client.close()


def claude_args(executable, model):
    return [executable, '-p', '--model', model, '--output-format', 'stream-json', '--verbose',
        '--include-partial-messages', '--tools', '', '--disallowedTools', '*',
        '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--safe-mode',
        '--setting-sources', '', '--settings', '{"disableAllHooks":true}',
        '--no-session-persistence', '--no-chrome', '--max-turns', '1']


def claude_generate(row, messages, directory, on_preview):
    env = client_environment('claude-subscription', directory)
    with tempfile.TemporaryDirectory(prefix='notetaker-context-') as cwd:
        try:
            status = subprocess.run([row['executable'], 'auth', 'status'], env=env, cwd=cwd,
                capture_output=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            auth = json.loads(status.stdout)
            if status.returncode or auth.get('authMethod') != 'claude.ai': raise ValueError('not_subscription')
        except (OSError, ValueError, subprocess.SubprocessError):
            raise NoteFailure('provider_authentication') from None
        client = ClientProcess(claude_args(row['executable'], row['model']), env, cwd)
        try:
            client.process.stdin.write('\n\n'.join(m['content'] for m in messages).encode())
            client.process.stdin.close()
            text = ''
            while True:
                event = client.event()
                if event.get('type') == 'stream_event':
                    part = event.get('event', {})
                    if part.get('type') == 'content_block_start' and part.get('content_block', {}).get('type') == 'tool_use':
                        raise NoteFailure('unexpected_tool_request')
                    text += part.get('delta', {}).get('text', '')
                    if on_preview: on_preview(preview_text(text))
                if event.get('type') == 'result':
                    if event.get('is_error') or event.get('subtype') != 'success': raise NoteFailure('provider_limit_or_failure')
                    return event.get('result') or text, {'client':'claude-code', 'billing':'subscription', 'usage':event.get('usage', {})}
        finally:
            client.close()


def subscription_generate(provider, row, messages, directory, on_preview):
    try:
        if provider == 'chatgpt': return codex_generate(row, messages, directory, on_preview)
        return claude_generate(row, messages, directory, on_preview)
    except (OSError, ValueError, KeyError, TypeError):
        raise NoteFailure('subscription_client_unavailable') from None


def sign_in(provider, executable, directory):
    env = client_environment(provider, directory)
    if provider == 'chatgpt':
        args = [executable, 'login', '-c', 'cli_auth_credentials_store="keyring"']
    else:
        args = [executable, 'auth', 'login']
    try:
        result = subprocess.run(args, env=env, cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=180, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode: raise ValueError('Sign-in did not finish. Try again using the official provider client.')
    except subprocess.TimeoutExpired:
        raise ValueError('Sign-in timed out. Try again and finish in the browser within three minutes.') from None


def sign_out(provider, executable, directory):
    env = client_environment(provider, directory)
    args = [executable, 'logout', '-c', 'cli_auth_credentials_store="keyring"'] if provider == 'chatgpt' else [executable, 'auth', 'logout']
    result = subprocess.run(args, env=env, cwd=directory, capture_output=True, timeout=30,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('Provider sign-out failed. Sign out through the official client.')
