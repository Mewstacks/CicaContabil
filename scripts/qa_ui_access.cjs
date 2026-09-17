// Uses one-time synthetic links prepared in the isolated QA database.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const contrast=require('./qa_ui_contrast.cjs');
const base='http://127.0.0.1:8011';
const links=JSON.parse(fs.readFileSync('.tmp/ui-review/access-links.json','utf8'));
const rows=process.env.QA_ACCESS_KINDS ? JSON.parse(fs.readFileSync('.playwright-mcp/ui-review/access-regression.json','utf8')).filter(x=>x.kind!=='reset'&&x.kind!=='learning empty') : [];
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  for(const kind of (process.env.QA_ACCESS_KINDS || 'signup,invite,reset').split(',')){
   const ctx=await browser.newContext();const p=await ctx.newPage();
   await ctx.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
   await p.goto(base+links[kind]);
   const target=p.url();
   for(const theme of ['light','dark'])for(const width of [1440,390]){
    await ctx.addCookies([{name:'hub_theme',value:theme,url:base}]);
    await p.setViewportSize({width,height:960});await p.goto(target);
    assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    const file=`.playwright-mcp/ui-review/access-${kind}-${theme}-${width}.png`;
    await p.screenshot({path:file});rows.push({kind,theme,width,file,contrast:await p.evaluate(contrast)});
   }
   const inputs=p.locator('input[type=password]');
   for(let i=0;i<await inputs.count();i++)await inputs.nth(i).fill('synthetic-new-password-123');
   await p.locator('main button[type=submit]').click();await p.waitForLoadState();
   if(kind==='reset')assert(p.url().endsWith('/recuperar-senha/concluida/'));
   else assert(p.url().includes('/app/'));
   rows.push({kind,result:'completed'});
   const retry=await p.goto(base+links[kind]);
   if(kind!=='reset')assert.equal(retry.status(),410);
   else await p.getByRole('heading',{name:'Este link não está disponível.'}).waitFor();
   rows.push({kind,result:'reuse rejected'});
   await ctx.close();
  }
  const ctx=await browser.newContext();const p=await ctx.newPage();
  await ctx.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
  await p.goto(base+'/entrar/');await p.locator('[name=username]').fill('demo@hubcontador.local');
  await p.locator('[name=password]').fill('persona-local-password-123');
  await p.locator('button[type=submit]').first().click();await p.waitForLoadState();
  for(const theme of ['light','dark'])for(const width of [1440,390]){
   await ctx.addCookies([{name:'hub_theme',value:theme,url:base}]);await p.setViewportSize({width,height:960});
   const response=await p.goto(base+'/app/ia/aprendizado/');assert.equal(response.status(),200);
   await p.getByRole('heading',{name:'Central de aprendizado',exact:true}).waitFor();
   const file=`.playwright-mcp/ui-review/learning-${theme}-${width}.png`;
   await p.screenshot({path:file});rows.push({kind:'learning empty',theme,width,file,contrast:await p.evaluate(contrast)});
  }
  await ctx.close();
 }finally{await browser.close();fs.writeFileSync('.playwright-mcp/ui-review/access-regression.json',JSON.stringify(rows,null,2));}
 console.log(JSON.stringify({screens:rows.filter(x=>x.file).length,flows:rows.filter(x=>x.result),contrast:rows.filter(x=>x.contrast?.length)}));
})().catch(e=>{console.error(e.message.replace(/\/comecar\/verificar\/[^/]+/g,'/comecar/verificar/[redacted]').replace(/\/ativar\/[^/]+/g,'/ativar/[redacted]'));process.exitCode=1;});
