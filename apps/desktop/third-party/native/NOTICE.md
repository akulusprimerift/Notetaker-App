# Bundled standalone runtime notices

The SQLite standalone installer includes Python 3.12 and its SQLite library, Ollama 0.33.3 CPU libraries, and packages pinned in `apps/api/requirements-windows.lock`. Python/package metadata and available notices are retained here. Next/React and Electron licenses accompany their runtimes. PostgreSQL, SeaweedFS, Kafka and their client packages are excluded from the app.

- SQLite (public domain): https://www.sqlite.org/copyright.html
- Ollama: https://github.com/ollama/ollama/releases/tag/v0.33.3
- Python: https://www.python.org/doc/copyright/
- PyInstaller: https://pyinstaller.org/en/stable/license.html

No student speech or note model is bundled. Faster-whisper's upstream auxiliary VAD asset is part of the speech runtime. Users select existing local model files; the app never pulls weights. The legacy-conversion dependencies are maintenance tools and are not included in the standalone app.
