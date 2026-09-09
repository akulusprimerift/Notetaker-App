import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QLabel
from notetaker_native.client import Api, background
from notetaker_native.runtime import Runtime
from notetaker_native.window import Window


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--smoke-test', type=Path)
    args = parser.parse_args()
    if args.smoke_test and not args.data_dir:
        parser.error('Synthetic verification requires an explicit isolated --data-dir')
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('Notetaker'); app.setOrganizationName('Notetaker')
    directory = args.data_dir or Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'NotetakerNative'
    directory.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(directory/'application.lock'))
    if not lock.tryLock(0):
        QMessageBox.information(None, 'Notetaker is already open', 'This library is already open in another Notetaker window.')
        return 1
    runtime = Runtime(directory)
    loading = QLabel('Opening your local Notetaker library…'); loading.resize(420,100); loading.show()
    windows = []
    def ready(_):
        window = Window(Api(runtime.url), runtime); windows.append(window); window.show()
        loading.close()
        app.setQuitOnLastWindowClosed(True)
        if args.smoke_test:
            from notetaker_native.smoke import run
            QTimer.singleShot(3000, lambda:run(window, args.smoke_test, app))
    def failed(message):
        loading.close()
        if args.smoke_test:
            import json
            args.smoke_test.mkdir(parents=True, exist_ok=True)
            (args.smoke_test/'report.json').write_text(json.dumps({'error':message}), encoding='utf-8')
        else:
            QMessageBox.critical(None, 'Notetaker could not open', message)
        app.exit(1)
    background(runtime.start, ready, failed)
    try:
        return app.exec()
    finally:
        runtime.close(); lock.unlock()


if __name__ == '__main__':
    raise SystemExit(main())
