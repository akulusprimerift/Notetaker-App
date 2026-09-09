module.exports = {
  appId:'com.notetaker.desktop', productName:'Notetaker',
  directories:{output:'.local/desktop-dist'},
  files:['apps/desktop/**/*','package.json'],
  extraResources:['package.json','bun.lock','compose.yaml','alembic.ini','.dockerignore',
    'apps/web','apps/api','contracts/ai','prompts','infra',
    'scripts/Start-App.ps1','scripts/Initialize-Services.ps1'].map(from=>({from,to:'service-source/'+from,
      filter:['**/*','!**/node_modules/**','!**/.next/**','!**/__pycache__/**','!**/*.tsbuildinfo']})),
  asar:true, npmRebuild:false,
  win:{target:[{target:'nsis',arch:['x64']}],icon:'apps/desktop/icon.ico',signExecutable:false},
  nsis:{oneClick:false,perMachine:false,allowToChangeInstallationDirectory:true,
    createDesktopShortcut:true,createStartMenuShortcut:true,deleteAppDataOnUninstall:false,runAfterFinish:false},
  artifactName:'Notetaker-${version}-Setup.${ext}',
};
