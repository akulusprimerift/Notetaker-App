const {desktopPlatform}=require('./apps/desktop/platform.cjs');
const target=desktopPlatform();
if(!process.env.NOTETAKER_NATIVE_RESOURCES)throw new Error('Prepare the standalone SQLite runtime before packaging.');
const helperRoot=`node_modules/@openai/${target.helperPackage}`;
module.exports = {
  appId:'com.notetaker.desktop', productName:'Notetaker',
  directories:{output:'.local/windows-standalone-dist'},
  files:['apps/desktop/**/*','package.json'],
  extraResources:[{from:`${helperRoot}/vendor/${target.helperVendor}`,to:'account-client'},
    {from:`${helperRoot}/README.md`,to:'account-client/README.md'}].concat(process.env.NOTETAKER_NATIVE_RESOURCES?[{from:process.env.NOTETAKER_NATIVE_RESOURCES,to:'native-runtime'}]:[]),
  asar:true, npmRebuild:false,
  // Avoid recompressing the large native runtime during development packaging.
  compression:process.env.NOTETAKER_NATIVE_RESOURCES?'store':'normal',
  win:{target:[{target:'nsis',arch:['x64']}],icon:'apps/desktop/icon.ico',signExecutable:false},
  nsis:{oneClick:false,perMachine:false,allowToChangeInstallationDirectory:true,
    createDesktopShortcut:true,createStartMenuShortcut:true,deleteAppDataOnUninstall:false,runAfterFinish:false},
  artifactName:'Notetaker-${version}-Windows-Standalone-Setup.${ext}',
};
