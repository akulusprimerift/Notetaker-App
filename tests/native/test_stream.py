import time
from types import SimpleNamespace
import httpx
from PySide6.QtWidgets import QApplication, QPlainTextEdit
from notetaker_native.client import Stream


def test_native_stream_delivers_partial_prose_as_literal_text():
    app = QApplication.instance() or QApplication([])
    def transport(request):
        return httpx.Response(200,content=b'data: {"active":true,"text":"Partial <script>lecture</script>"}\n\n',
                              headers={'content-type':'text/event-stream'})
    http = httpx.Client(base_url='http://127.0.0.1',transport=httpx.MockTransport(transport))
    stream = Stream(SimpleNamespace(http=http),'lecture')
    field = QPlainTextEdit()
    stream.changed.connect(lambda _,payload:field.setPlainText(payload['text']))
    stream.thread.start()
    try:
        deadline = time.monotonic()+3
        while not field.toPlainText() and time.monotonic()<deadline:
            app.processEvents(); time.sleep(.01)
        assert field.toPlainText()=='Partial <script>lecture</script>'
    finally:
        stream.stop.set(); stream.thread.join(timeout=2); http.close()
    assert not stream.thread.is_alive()
