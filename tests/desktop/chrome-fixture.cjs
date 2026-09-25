// Isolated native chrome qualification: no backend, user library or capture.
const {app,BrowserWindow}=require('electron');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../../apps/desktop/main.cjs'),'utf8');
const palettes=source.match(/const palettes = .*;/)[0];
const chrome=source.match(/function chromeOptions\(\).*\}/)[0];
const options=vm.runInNewContext(`${palettes}\nlet appearance='dark';\n${chrome}\nchromeOptions()`);
app.setPath('userData',app.commandLine.getSwitchValue('user-data-dir'));
app.whenReady().then(()=>{new BrowserWindow({...options,width:1360,height:950,show:false,webPreferences:{sandbox:true,contextIsolation:true,nodeIntegration:false}}).loadURL('about:blank');});
app.on('window-all-closed',()=>app.quit());
