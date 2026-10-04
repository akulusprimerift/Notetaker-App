# Bundled Windows runtime notices

The standalone installer includes SeaweedFS 4.47, Ollama 0.33.3 CPU libraries, Python 3.12.14 and packages pinned in `apps/api/requirements-windows.lock`. PostgreSQL server binaries are not part of the application runtime. The optional PostgreSQL-to-SQLite conversion command uses the separately pinned Psycopg client driver in that lock; it connects only when explicitly invoked. Ollama dependency notices accompany their runtime files. Python/package metadata and available license/notice files are retained in this folder. Next/React and Electron licenses accompany their respective bundled runtimes.

Source distributions and license references:

- SeaweedFS: https://github.com/seaweedfs/seaweedfs/releases/tag/4.47
- Ollama: https://github.com/ollama/ollama/releases/tag/v0.33.3
- Python: https://www.python.org/doc/copyright/
- PyInstaller: https://pyinstaller.org/en/stable/license.html

No user speech or note model is included. The faster-whisper package contains its upstream auxiliary VAD asset as part of the speech runtime. Users select their own faster-whisper model folder and installed local Ollama models. The app never pulls model weights.
