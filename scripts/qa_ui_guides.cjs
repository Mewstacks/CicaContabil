// Regression for the collapsed action column with 2,945 synthetic calculations.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const contrast=require('./qa_ui_contrast.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const results=[];
 try{
  const ctx=await browser.newContext();const p=await ctx.newPage();p.setDefaultTimeout(8000);
  await ctx.route('**/*',r=>new URL(r.request().url()).origin==='http://127.0.0.1:8011'?r.continue():r.abort());
  await p.goto('http://127.0.0.1:8011/entrar/');
  await p.locator('[name=username]').fill('demo@hubcontador.local');await p.locator('[name=password]').fill('persona-local-password-123');
  await p.locator('button[type=submit]').first().click();await p.waitForLoadState();
  await p.locator('[data-popover-toggle=office-list]').click();await p.locator('#office-list button').filter({hasText:'Escritório QA'}).click();
  for(const theme of ['light','dark'])for(const width of [1440,1024,768,390,375]){
   await ctx.addCookies([{name:'hub_theme',value:theme,url:'http://127.0.0.1:8011'}]);await p.setViewportSize({width,height:960});
   await p.goto('http://127.0.0.1:8011/app/guias/');
   await p.locator('.guide-calculation-table').waitFor();
   const metrics=await p.locator('.guide-calculation-table').evaluate(table=>({
    rows:table.querySelectorAll('tbody tr').length,
    rowHeights:[...table.querySelectorAll('tbody tr')].map(r=>Math.round(r.getBoundingClientRect().height)),
    actionWidths:[...table.querySelectorAll('.row-action-button')].map(a=>Math.round(a.getBoundingClientRect().width)),
    overflow:document.documentElement.scrollWidth>innerWidth,
   }));
   assert.equal(metrics.rows,30);assert.equal(metrics.overflow,false);
   assert(metrics.actionWidths.every(w=>w>=86));
   if(width>1100)assert(metrics.rowHeights.every(h=>h<160));
   await p.locator('#dominio-calculations-heading').evaluate(e=>window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY-100));
   const file=`.playwright-mcp/ui-review/guides-fixed-${theme}-${width}.png`;
   await p.screenshot({path:file});
   results.push({theme,width,...metrics,contrast:await p.evaluate(contrast),file});
  }
  await p.setViewportSize({width:1440,height:960});
  await p.locator('[data-guide-select-all]').check();
  assert.equal(await p.locator('[data-guide-target]:checked').count(),30);
  assert(await p.locator('[data-guide-bulk-actions]').isVisible());
  await p.setViewportSize({width:390,height:960});
  await p.locator('[data-guide-selection-count]').evaluate(e=>window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY-100));
  await p.screenshot({path:'.playwright-mcp/ui-review/guides-selected-mobile.png'});
  await p.setViewportSize({width:1440,height:960});
  await p.getByRole('link',{name:'Próxima',exact:true}).click();await p.waitForLoadState();
  assert(p.url().includes('apuracao_pagina=2'));
  await p.locator('.pagination-status').filter({hasText:'31–60'}).waitFor();
  await p.locator('#guide-search').fill('QA239');await p.getByRole('button',{name:'Filtrar',exact:true}).click();
  await p.waitForLoadState();
  assert.equal(await p.locator('.guide-calculation-table tbody tr').count(),12);
  await p.locator('.guide-calculation-table .row-action-button').first().click();
  await p.getByRole('heading',{name:'Consultar DCTFWeb',exact:true}).waitFor();
  results.push({interaction:'select page, next page, filter, open consultation',status:'passed'});
  await ctx.close();
  const readOnly=await browser.newContext();const audit=await readOnly.newPage();
  await readOnly.route('**/*',r=>new URL(r.request().url()).origin==='http://127.0.0.1:8011'?r.continue():r.abort());
  await audit.goto('http://127.0.0.1:8011/entrar/');
  await audit.locator('[name=username]').fill('auditor@hubcontador.local');
  await audit.locator('[name=password]').fill('persona-local-password-123');
  await audit.locator('button[type=submit]').first().click();await audit.waitForLoadState();
  for(const theme of ['light','dark'])for(const width of [1440,390]){
   await readOnly.addCookies([{name:'hub_theme',value:theme,url:'http://127.0.0.1:8011'}]);
   await audit.setViewportSize({width,height:960});
   await audit.goto('http://127.0.0.1:8011/app/integra-contador/parcelamentos/');
   await audit.getByText('Somente leitura.',{exact:false}).waitFor();
   assert.equal(await audit.locator('#parcelamento-submit').count(),0);
   assert.equal(await audit.locator('[name=selected_company]').count(),0);
   assert.equal(await audit.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const file=`.playwright-mcp/ui-review/parcelamentos-auditor-${theme}-${width}.png`;
   await audit.screenshot({path:file});results.push({interaction:'auditor read-only portfolio',theme,width,status:'passed',file,contrast:await audit.evaluate(contrast)});
  }
  await audit.goto('http://127.0.0.1:8011/app/integra-contador/dte/');
  await audit.locator('.dte-service-nav').getByRole('link',{name:'Parcelamentos',exact:true}).click();
  assert(audit.url().endsWith('/parcelamentos/'));
  results.push({interaction:'DTE navigation to parcelamentos',status:'passed'});
  await readOnly.close();
 }finally{await browser.close();fs.writeFileSync('.playwright-mcp/ui-review/guides-fixed.json',JSON.stringify(results,null,2));}
 console.log(JSON.stringify(results.map(r=>({width:r.width,theme:r.theme,rows:r.rows,maxHeight:r.rowHeights&&Math.max(...r.rowHeights),overflow:r.overflow,contrast:r.contrast,status:r.status}))));
})().catch(e=>{console.error(e);process.exitCode=1;});
