import json
import threading
from uuid import uuid4
import httpx
from PySide6.QtCore import QObject, Signal, Slot, Qt, QRunnable, QThreadPool


class Api:
    def __init__(self, url):
        self.url = url
        self.http = httpx.Client(base_url=url, timeout=30, trust_env=False, headers={'Origin':url})
        session = self.request('POST', '/session/open')
        self.http.headers['x-csrf-token'] = session['csrf_token']

    def request(self, method, path, **kwargs):
        headers = {'idempotency-key':str(uuid4()), **kwargs.pop('headers', {})}
        response = self.http.request(method, path, headers=headers, **kwargs)
        if response.is_error:
            try:
                message = response.json()['error']['message']
            except (ValueError, KeyError):
                message = 'The local service could not complete this request.'
            raise RuntimeError(message)
        if 'application/json' in response.headers.get('content-type', ''):
            return response.json()
        return response.content

    def get(self, path):
        return self.request('GET', path)

    def post(self, path, body=None, **kwargs):
        return self.request('POST', path, json=body or {}, **kwargs)


class Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


_tasks = set()


class Completion(QObject):
    def __init__(self, task, done, failed):
        super().__init__()
        self.task, self.done, self.failed = task, done, failed

    @Slot(object)
    def success(self, value):
        try:
            self.done(value)
        finally:
            _tasks.discard(self.task)
            self.deleteLater()

    @Slot(str)
    def failure(self, message):
        try:
            self.failed(message)
        finally:
            _tasks.discard(self.task)
            self.deleteLater()


class Task(QRunnable):
    def __init__(self, function, done, failed):
        super().__init__()
        self.function = function
        self.signals = Signals()
        self.completion = Completion(self, done, failed)
        self.signals.done.connect(self.completion.success, Qt.ConnectionType.QueuedConnection)
        self.signals.failed.connect(self.completion.failure, Qt.ConnectionType.QueuedConnection)

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as exc:
            self.signals.failed.emit(str(exc))


def background(function, done, failed):
    task = Task(function, done, failed)
    _tasks.add(task)
    QThreadPool.globalInstance().start(task)


class Stream(QObject):
    changed = Signal(str, object)

    def __init__(self, api, lecture):
        super().__init__()
        self.stop = threading.Event()
        self.api, self.lecture = api, lecture
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            try:
                with self.api.http.stream('GET', '/lectures/'+self.lecture+'/notes/stream', timeout=5) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if self.stop.is_set():
                            return
                        if line.startswith('data: '):
                            self.changed.emit(self.lecture, json.loads(line[6:]))
                self.stop.wait(1)
            except (httpx.HTTPError, ValueError):
                self.changed.emit(self.lecture, {'active':False, 'text':'Connection interrupted. Reconnecting…'})
                self.stop.wait(2)
