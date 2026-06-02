// 🍅 番茄钟 — Electron 主进程
const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain, shell } = require('electron');
const path = require('path');

let win = null;
let tray = null;
let quitting = false;

// ── 单实例锁 ──
const locked = app.requestSingleInstanceLock();
if (!locked) { app.quit(); }

app.on('second-instance', () => {
  if (win) {
    win.show();
    win.focus();
    if (win.isMinimized()) win.restore();
  }
});

// ── 创建窗口 ──
function createWindow() {
  win = new BrowserWindow({
    width: 420,
    height: 660,
    minWidth: 360,
    minHeight: 580,
    resizable: true,
    frame: false,                    // 无边框 → 自定义标题栏
    transparent: false,
    backgroundColor: '#0f0f1a',
    title: '🍅 番茄钟',
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.loadFile('pomodoro.html');

  win.once('ready-to-show', () => win.show());

  win.on('close', e => {
    if (!quitting) {
      e.preventDefault();
      win.hide();
    }
  });
}

// ── 系统托盘 ──
function createTray() {
  // 像素级绘制番茄图标
  const size = 32;
  const buf = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const cx = 16, cy = 17, r = 12;
      const d = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
      if (d <= r) {
        buf[i] = 0xE7; buf[i+1] = 0x4C; buf[i+2] = 0x3C; buf[i+3] = 0xFF;
      } else if (y <= 6 && x >= 13 && x <= 19 && y >= 2) {
        buf[i] = 0x2E; buf[i+1] = 0xCC; buf[i+2] = 0x71; buf[i+3] = 0xFF;
      } else {
        buf[i+3] = 0x00;
      }
    }
  }
  const icon = nativeImage.createFromBuffer(buf, { width: size, height: size });

  tray = new Tray(icon);
  tray.setToolTip('🍅 番茄钟');

  tray.setContextMenu(Menu.buildFromTemplate([
    {
      label: '显示番茄钟',
      click: () => { win.show(); win.focus(); },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => { quitting = true; app.quit(); },
    },
  ]));

  tray.on('double-click', () => { win.show(); win.focus(); });
}

// ── IPC：窗口控制 ──
ipcMain.on('win-minimize', () => win?.minimize());
ipcMain.on('win-close', () => win?.close());
ipcMain.on('win-toggle-always-on-top', (_e, flag) => {
  win?.setAlwaysOnTop(flag);
});

// ── 应用生命周期 ──
app.whenReady().then(() => {
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
    else win?.show();
  });
});

app.on('before-quit', () => { quitting = true; });

// 防止后台挂住（Windows 关闭最后一个隐藏窗口后不退）
app.on('window-all-closed', () => {});
