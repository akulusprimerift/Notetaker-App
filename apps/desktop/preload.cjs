'use strict';
const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('desktopSetup', Object.freeze({
  status: () => ipcRenderer.invoke('setup:status'),
  start: () => ipcRenderer.invoke('setup:start'),
  native: () => ipcRenderer.invoke('setup:native'),
  stopNative: () => ipcRenderer.invoke('setup:stop-native'),
  open: () => ipcRenderer.invoke('setup:open'),
  models: () => ipcRenderer.invoke('setup:models'),
  speechFolder: () => ipcRenderer.invoke('setup:speech-folder'),
  workspaceFolder: () => ipcRenderer.invoke('setup:workspace-folder'),
}));
contextBridge.exposeInMainWorld('desktopApp', Object.freeze({
  appearance: value => ipcRenderer.invoke('app:appearance',value),
  openSetup: () => ipcRenderer.invoke('app:open-setup'),
  chooseSpeech: () => ipcRenderer.invoke('app:choose-speech'),
  openSpeechGuide: () => ipcRenderer.invoke('app:speech-guide'),
}));
