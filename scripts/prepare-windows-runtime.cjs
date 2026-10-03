'use strict';
const fs=require('node:fs/promises');
const path=require('node:path');
const {randomUUID,createHash}=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {inventory}=require('./prepare-desktop-web.cjs');

const sources=[
  {name:'seaweedfs',version:'4.47',archive:'.local/windows-runtime-vendor/seaweed-4.47.zip',
    url:'https://github.com/seaweedfs/seaweedfs/releases/download/4.47/windows_amd64.zip',sha256:'8809359079e62fcd60574ff661449160899622c52072f3f569d346669079efe9'},
  {name:'ollama',version:'0.33.3',archive:'.local/native-vendor/ollama-windows-amd64.zip',
    url:'https://github.com/ollama/ollama/releases/download/v0.33.3/ollama-windows-amd64.zip',sha256:'52cb36a62e7e501f61514f60212dec7117b6c098811357585e02fffe32d2fcd7'},
];
async function main(){
  const root=path.resolve(__dirname,'..'),web=path.resolve(process.argv[2]||'');
  if(!process.argv[2])throw new Error('Pass the verified desktop web bundle directory.');
  for(const source of sources){
    const bytes=await fs.readFile(path.join(root,source.archive));
    if(createHash('sha256').update(bytes).digest('hex')!==source.sha256)throw new Error(source.name+' archive hash mismatch.');
  }
  const destination=path.join(root,'.local/windows-runtime',randomUUID());
  await fs.mkdir(destination,{recursive:true});
  const copy=async(from,to)=>fs.cp(path.join(root,from),path.join(destination,to),{recursive:true});
  await fs.cp(web,path.join(destination,'web'),{recursive:true});
  await copy('.local/windows-service-dist/NotetakerService','service');
  for(const source of sources){
    const component=source.name==='seaweedfs'?'seaweed':'ollama';
    execFileSync('uv',['run','--no-project','python',path.join(root,'scripts/extract-windows-vendor.py'),
      path.join(root,source.archive),path.join(destination,component),component],{windowsHide:true,stdio:'inherit'});
  }
  await copy('apps/desktop/third-party/native','notices');
  const webManifest=JSON.parse(await fs.readFile(path.join(web,'bundle-manifest.json'),'utf8'));
  const files=await inventory(destination);
  await fs.writeFile(path.join(destination,'runtime-manifest.json'),JSON.stringify({schema_version:1,platform:'win32',arch:'x64',
    profile:'windows-sqlite-seaweed-reconciliation',web_build_id:webManifest.build_id,
    user_models_bundled:false,ollama_compute:'CPU',sources,files},null,2)+'\n');
  console.log('Prepared native runtime: '+destination);
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
