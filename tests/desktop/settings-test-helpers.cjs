async function setTheme(page,theme){
  const dialog=page.getByRole('dialog',{name:'Settings'});
  await page.getByRole('button',{name:'Settings',exact:true}).click();
  await dialog.waitFor();
  await dialog.getByLabel('App theme').selectOption(theme);
  await page.keyboard.press('Escape');
  await dialog.waitFor({state:'hidden'});
}

module.exports={setTheme};
