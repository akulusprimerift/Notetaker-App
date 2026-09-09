# Native distribution components

The application ships dynamically linked Qt/PySide6 6.11.2, Python and the packages pinned in `apps/api/requirements-native.lock`. Wheel metadata, available license files, GPL/LGPL texts and Ollama's license are collected under `_internal/third-party-notices`. Ollama's additional bundled notices remain in its vendor directory. Qt DLLs remain separate and replaceable; no Qt or PySide6 source modifications are made by this application.

Upstream source locations: [Qt 6.11.2](https://download.qt.io/archive/qt/6.11/6.11.2/), [PySide source](https://code.qt.io/cgit/pyside/pyside-setup.git/), [Ollama v0.33.3](https://github.com/ollama/ollama/tree/v0.33.3), [Python](https://www.python.org/downloads/source/), and the project/source links in each dependency's packaged metadata. The application source and reproducible build specification are included in `_internal/application-source`; model weights are not included.
