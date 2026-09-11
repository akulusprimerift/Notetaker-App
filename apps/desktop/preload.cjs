'use strict';
const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('desktopSetup', Object.freeze({
  status: () => ipcRenderer.invoke('setup:status'),
  start: () => ipcRenderer.invoke('setup:start'),
  open: () => ipcRenderer.invoke('setup:open'),
  models: () => ipcRenderer.invoke('setup:models'),
  speechFolder: () => ipcRenderer.invoke('setup:speech-folder'),
  workspaceFolder: () => ipcRenderer.invoke('setup:workspace-folder'),
}));
contextBridge.exposeInMainWorld('desktopApp', Object.freeze({
  openSetup: () => ipcRenderer.invoke('app:open-setup'),
  chooseProviderClient: () => ipcRenderer.invoke('provider:choose-client'),
}));
