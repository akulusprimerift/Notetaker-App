const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const {inventory} = require('../../scripts/prepare-desktop-web.cjs');

test('web bundle inventory hashes assets and rejects copied private configuration', async()=>{
  const directory = await fs.mkdtemp(path.join(os.tmpdir(),'notetaker-web-bundle-'));
  try {
    await fs.writeFile(path.join(directory,'asset.js'),'synthetic');
    const first = await inventory(directory);
    await fs.writeFile(path.join(directory,'asset.js'),'changed');
    assert.notEqual((await inventory(directory))[0].sha256, first[0].sha256);
    await fs.writeFile(path.join(directory,'.env.local'),'SYNTHETIC_SECRET');
    await assert.rejects(inventory(directory), /Private configuration/);
  } finally {
    assert.equal(path.dirname(path.resolve(directory)),path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('notetaker-web-bundle-'));
    await fs.rm(directory,{recursive:true,force:true});
  }
});
