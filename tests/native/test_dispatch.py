import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from notetaker_native.client import background


def test_service_results_are_delivered_on_the_gui_thread():
    app = QApplication.instance() or QApplication([])
    received = []
    background(lambda:'result', lambda value:received.append((value,QThread.currentThread())),
               lambda error:received.append(error))
    deadline = time.monotonic()+5
    while not received and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.01)
    assert received == [('result',app.thread())]
