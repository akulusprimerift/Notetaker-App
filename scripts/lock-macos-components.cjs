'use strict';
const path=require('node:path');
const {requireMac,lockComponents}=require('./macos-runtime.cjs');
Promise.resolve().then(()=>{
  requireMac();
  if(process.argv.length!==3)throw new Error('Usage: bun run lock:macos-runtime <component-sources.json>');
  return lockComponents({root:path.resolve(__dirname,'..'),descriptorPath:path.resolve(process.argv[2])});
}).then(lock=>console.log('Local component inventory lock (review provenance before packaging): '+lock))
  .catch(error=>{console.error(error.message);process.exitCode=1;});
