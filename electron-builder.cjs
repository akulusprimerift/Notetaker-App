const {desktopPlatform}=require('./apps/desktop/platform.cjs');
const target=desktopPlatform();
const helperRoot=`node_modules/@openai/${target.helperPackage}`;
module.exports = {
  appId:'com.notetaker.desktop', productName:'Notetaker',
  directories:{output:process.env.NOTETAKER_NATIVE_RESOURCES?'.local/windows-standalone-dist':'.local/desktop-dist'},
  files:['apps/desktop/**/*','package.json'],
  extraResources:['package.json','bun.lock','compose.yaml','alembic.ini','.dockerignore',
    'apps/web','apps/api','contracts/ai','prompts','infra',
    'scripts/Start-App.ps1','scripts/Initialize-Services.ps1'].map(from=>({from,to:'service-source/'+from,
      filter:['**/*','!**/node_modules/**','!**/.next/**','!**/__pycache__/**','!**/*.tsbuildinfo']})).concat([{from:`${helperRoot}/vendor/${target.helperVendor}`,to:'account-client'}, {from:`${helperRoot}/README.md`,to:'account-client/README.md'}],process.env.NOTETAKER_NATIVE_RESOURCES?[{from:process.env.NOTETAKER_NATIVE_RESOURCES,to:'native-runtime'}]:[]),
  asar:true, npmRebuild:false,
  // Avoid recompressing the large native runtime during development packaging.
  compression:process.env.NOTETAKER_NATIVE_RESOURCES?'store':'normal',
  win:{target:[{target:'nsis',arch:['x64']}],icon:'apps/desktop/icon.ico',signExecutable:false},
  nsis:{oneClick:false,perMachine:false,allowToChangeInstallationDirectory:true,
    createDesktopShortcut:true,createStartMenuShortcut:true,deleteAppDataOnUninstall:false,runAfterFinish:false},
  artifactName:process.env.NOTETAKER_NATIVE_RESOURCES?'Notetaker-${version}-Windows-Standalone-Setup.${ext}':'Notetaker-${version}-Setup.${ext}',
};
