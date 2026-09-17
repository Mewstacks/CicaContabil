/* Extended synthetic journeys for qa_ui_server.py. No external requests. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const contrast=require('./qa_ui_contrast.cjs');
const base='http://127.0.0.1:8011';
const out='.playwright-mcp/ui-review';
const rows=[];
const localAuthenticator = () => execFileSync('.venv/Scripts/python.exe', ['-c', [
  'import os,sys;from pathlib import Path',
  'sys.path.insert(0,str(Path.cwd()/"src"))',
  'os.environ["DJANGO_SETTINGS_MODULE"]="config.settings.test"',
  'os.environ["TEST_SQLITE_PATH"]=str(Path.cwd()/".tmp/ui-review/db.sqlite3")',
  'import django;django.setup()',
  'from apps.accounts.models import User',
  'from apps.accounts import mfa,totp',
  'device=mfa.device_for(User.objects.get(email="dev@hubcontador.local"))',
  'print(totp.code_for(device.secret,totp.counter_at()))',
].join(';')], {encoding:'utf8',stdio:['ignore','pipe','ignore']}).trim();
const otp=secret=>{
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits=[...secret].map(c=>alphabet.indexOf(c).toString(2).padStart(5,'0')).join('');
  const key=Buffer.from(bits.match(/.{8}/g).map(b=>parseInt(b,2)));
  const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));
  const hash=crypto.createHmac('sha1',key).update(counter).digest();
  return String((hash.readUInt32BE(hash[19]&15)&0x7fffffff)%1000000).padStart(6,'0');
};
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const run=async(name,task)=>{
    const ctx=await browser.newContext({viewport:{width:390,height:960}});
    await ctx.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
    const p=await ctx.newPage();p.setDefaultTimeout(8000);
    const login=async user=>{await p.goto(base+'/entrar/');await p.locator('[name=username]').fill(user+'@hubcontador.local');await p.locator('[name=password]').fill('persona-local-password-123');await p.locator('button[type=submit]').first().click();await p.waitForLoadState();};
    try{const evidence=await task(p,login,ctx);rows.push({name,status:'passed',evidence});}
    catch(e){rows.push({name,status:'failed',error:e.message,url:p.url()});}
    finally{await ctx.close();console.log(name,rows.at(-1).status);}
  };
  try{
    await run('Platform configuration after required MFA, all sections',async(p,login,ctx)=>{
      await login('dev');await p.goto(base+'/platform/configuracoes/');
      if(p.url().includes('/mfa/configurar/')){
        const secret=await p.locator('#mfa-secret').innerText();
        await p.locator('[name=code]').fill(otp(secret));
        await p.getByRole('button',{name:'Confirmar',exact:true}).click();
        await p.locator('.auth-card a.button').first().click();
      } else if(p.url().includes('/mfa/entrar/')) {
        await p.locator('[name=code]').fill(localAuthenticator());
        await p.getByRole('button',{name:'Entrar',exact:true}).click();
      }
      await p.waitForLoadState();
      await p.goto(base+'/platform/configuracoes/');
      await p.locator('.configuration-page').waitFor();
      const sections=await p.locator('.configuration-nav a').evaluateAll(es=>es.map(e=>e.getAttribute('href')));
      const screens=[];
      for(const theme of ['light','dark'])for(const width of [1440,390]){
        await ctx.addCookies([{name:'hub_theme',value:theme,url:base}]);await p.setViewportSize({width,height:960});
        await p.goto(base+'/platform/configuracoes/');
        for(let i=0;i<sections.length;i++){
          await p.locator('.configuration-nav a').nth(i).click();
          const file=out+'/config-section-'+i+'-'+theme+'-'+width+'.png';
          await p.screenshot({path:file,fullPage:true});
          screens.push({section:sections[i],theme,width,overflow:await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),contrast:await p.evaluate(contrast),file});
        }
      }
      return screens;
    });
    await run('Support start and explicit end',async(p,login)=>{
      await login('suporte');await p.goto(base+'/platform/tenants/');
      await p.getByRole('link',{name:'Escritório Demonstração',exact:true}).click();
      await p.getByRole('button',{name:'Abrir área do escritório'}).click();
      await p.locator('.support-banner').waitFor();
      await p.screenshot({path:out+'/support-mobile.png',fullPage:false});
      const text=await p.locator('.support-banner').innerText();
      await p.getByRole('button',{name:'Encerrar suporte'}).click();
      await p.waitForURL('**/platform/**');
      return {banner:text,ended:p.url().includes('/platform/')};
    });
    await run('Office switch, large portfolio, pagination and permissions search',async(p,login)=>{
      await login('demo');await p.locator('[data-popover-toggle=office-list]').click();
      await p.locator('#office-list button').filter({hasText:'Escritório QA'}).click();
      await p.goto(base+'/app/empresas/');await p.getByRole('link',{name:'Próxima',exact:true}).click();
      assert(p.url().includes('pagina=2'));
      assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await p.screenshot({path:out+'/large-portfolio-mobile.png',fullPage:true});
      await p.goto(base+'/app/equipe/');
      const search=p.locator('.scope-search').first();await search.fill('239');
      const field=p.locator('.scope-picker').filter({has:search});
      await field.locator('label:visible input').check();await search.fill('001');
      assert.match(await field.locator('.scope-summary').innerText(),/1 selecionadas/);
      await p.screenshot({path:out+'/large-scope-mobile.png',fullPage:false});
      await p.locator('[data-popover-toggle=office-list]').click();
      p.once('dialog',d=>d.accept());
      await p.locator('#office-list button').filter({hasText:'Escritório Demonstração'}).click();
      await p.goto(base+'/app/empresas/');
      assert(!await p.locator('tbody').innerText().then(t=>t.includes('Empresa QA 239')));
      return {companies:240,pagination:true,selectionPreserved:true,officeIsolation:true};
    });
    await run('MFA enrollment, invalid code, recovery and login',async(p,login,ctx)=>{
      await login('mfa');
      if(!p.url().includes('/mfa/configurar/')) return {state:'already enrolled; enrollment evidence from previous run'};
      await p.locator('[name=code]').fill('invalid');await p.getByRole('button',{name:'Confirmar',exact:true}).click();
      await p.locator('.field-error').waitFor();
      const secret=await p.locator('#mfa-secret').innerText();
      const screens=[];
      for(const theme of ['light','dark'])for(const width of [1440,390]){
        await ctx.addCookies([{name:'hub_theme',value:theme,url:base}]);await p.setViewportSize({width,height:960});await p.reload();
        const file=out+'/mfa-'+theme+'-'+width+'.png';
        await p.screenshot({path:file,fullPage:true,mask:[p.locator('#mfa-secret'),p.locator('.mfa-qr')]});
        screens.push({theme,width,contrast:await p.evaluate(contrast),file});
      }
      const current=await p.locator('#mfa-secret').innerText();
      await p.locator('[name=code]').fill(otp(current));await p.getByRole('button',{name:'Confirmar',exact:true}).click();
      await p.locator('.recovery-codes').waitFor();
      const recovery=await p.locator('.recovery-codes code').first().innerText();
      await p.screenshot({path:out+'/mfa-recovery.png',fullPage:true,mask:[p.locator('.recovery-codes')]});
      await p.getByRole('link',{name:'Abrir área do escritório'}).click();
      await p.locator('[data-popover-toggle=account-list]').click();await p.getByRole('button',{name:'Sair',exact:true}).click();
      await login('mfa');await p.locator('[name=code]').fill(recovery);await p.locator('form button[type=submit]').first().click();
      await p.waitForURL('**/app/');return {enrolled:true,recovery:true,screens};
    });
    await run('DTE fictitious acknowledgment and evidence',async p=>{
      await p.goto(base+'/demo/');await p.getByRole('button',{name:'Iniciar demonstração fictícia'}).click();
      await p.goto(base+'/app/integra-contador/dte/');await p.getByRole('link',{name:/Ver resumo/}).first().click();
      await p.locator('[name=confirm_legal_notice]').check();await p.getByRole('button',{name:'Abrir teor fictício'}).click();
      await p.getByText('Aberta na demonstração',{exact:true}).waitFor();
      await p.reload();assert.equal(await p.getByRole('button',{name:'Abrir teor fictício'}).count(),0);
      await p.screenshot({path:out+'/dte-open-mobile.png',fullPage:true});return {repeatPrevented:true};
    });
    await run('Copilot synthetic response and source context',async p=>{
      await p.goto(base+'/demo/');await p.getByRole('button',{name:'Iniciar demonstração fictícia'}).click();
      await p.goto(base+'/app/ia/');const company=p.locator('#assistant-company');await company.selectOption(await company.locator('option').nth(1).getAttribute('value'));
      await p.locator('textarea').fill('Quais pendências precisam de revisão?');await p.getByRole('button',{name:'Enviar',exact:true}).click();
      await p.waitForLoadState();await p.locator('.question-composer').waitFor();
      assert.match(await p.locator('main').innerText(),/fict|simulad/i);
      await p.screenshot({path:out+'/copilot-response-mobile.png',fullPage:true});return {url:p.url(),externalCalls:false};
    });
    await run('Public, access and token error screens final audit',async(p,login,ctx)=>{
      const screens=[];const paths=['/','/entrar/','/comecar/','/demo/','/recuperar-senha/','/recuperar-senha/enviado/','/recuperar-senha/concluida/','/recuperar-senha/MQ/invalid/','/ativar/invalido/','/comecar/verificar/invalido/','/legal/termos/','/legal/privacidade/'];
      for(const theme of ['light','dark'])for(const width of [1440,390]){
        await ctx.addCookies([{name:'hub_theme',value:theme,url:base}]);await p.setViewportSize({width,height:960});
        for(let i=0;i<paths.length;i++){
          const response=await p.goto(base+paths[i]);const file=out+'/final-public-'+i+'-'+theme+'-'+width+'.png';await p.screenshot({path:file,fullPage:true});
          screens.push({path:paths[i],theme,width,status:response.status(),overflow:await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),contrast:await p.evaluate(contrast),file});
        }
      }
      return screens;
    });
  }finally{await browser.close();fs.writeFileSync(out+'/extended-regression.json',JSON.stringify(rows,null,2));console.log(JSON.stringify(rows.filter(r=>r.status==='failed')));if(rows.some(r=>r.status==='failed'))process.exitCode=1;}
})().catch(e=>{console.error(e);process.exitCode=1;});
