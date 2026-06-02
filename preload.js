// 🍅 番茄钟 — preload（安全桥接）
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('pomodoro', {
  minimize: () => ipcRenderer.send('win-minimize'),
  close:     () => ipcRenderer.send('win-close'),
  setAlwaysOnTop: (flag) => ipcRenderer.send('win-toggle-always-on-top', flag),
});
