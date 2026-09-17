/* Local fallback and repeatable regression for qa_ui_server.py.
 * PLAYWRIGHT_MODULE may point to an existing Playwright installation.
 * All contexts are synthetic; network is restricted to the isolated local server.
 */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const contrastProbe = require('./qa_ui_contrast.cjs');
const base = 'http://127.0.0.1:8011';
const output = '.playwright-mcp/ui-review';
fs.mkdirSync(output, { recursive: true });
const results = { flows: [], screens: [], errors: [] };
const password = 'persona-local-password-123';
let browser;
const check = async (name, task) => {
  try { const evidence = await task(); results.flows.push({ name, status: 'passed', evidence }); }
  catch (error) { results.flows.push({ name, status: 'failed', error: error.message }); }
  console.log(name, results.flows.at(-1).status);
};
const context = async () => {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  await ctx.route('**/*', route => {
    const url = new URL(route.request().url());
    return url.origin === base || ['data:', 'blob:'].includes(url.protocol)
      ? route.continue() : route.abort();
  });
  return ctx;
};
const login = async (page, name = 'demo') => {
  await page.goto(base + '/entrar/');
  await page.locator('[name=username]').fill(name + '@hubcontador.local');
  await page.locator('[name=password]').fill(password);
  await page.locator('button[type=submit]').first().click();
  await page.waitForLoadState();
};
const scan = async (page, paths, prefix) => {
  for (const theme of ['light', 'dark']) {
    await page.context().addCookies([{ name: 'hub_theme', value: theme, url: base }]);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 960 });
      for (let index = 0; index < paths.length; index++) {
        const path = paths[index];
        const response = await page.goto(base + path);
        const facts = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          h1: [...document.querySelectorAll('h1')].map(e => e.textContent.trim()),
          crampedActions: [...document.querySelectorAll('.table-action-cell a,.table-action-cell button')]
            .filter(e => e.getClientRects().length && e.getBoundingClientRect().width < 44 && e.getBoundingClientRect().height > 44)
            .map(e => e.textContent.trim()),
          unlabeled: [...document.querySelectorAll('input:not([type=hidden]),select,textarea,button')]
            .filter(e => e.getClientRects().length && !e.closest('[hidden]'))
            .filter(e => !e.labels?.length && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby') && !e.textContent.trim())
            .map(e => e.id || e.name || e.outerHTML.slice(0,100)),
        }));
        const file = `${output}/final-${prefix}-${index}-${theme}-${width}.png`;
        await page.screenshot({ path: file, fullPage: response.status() < 500, mask: [page.locator('[data-mfa-secret],.mfa-secret,.mfa-qr,code')] });
        const contrast = await page.evaluate(contrastProbe);
        results.screens.push({ path, actualUrl: page.url(), theme, width, status: response.status(), ...facts, contrast, file });
      }
    }
  }
};
(async () => {
  browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const ctx = await context();
  const page = await ctx.newPage();
  page.setDefaultTimeout(8000);
  page.on('pageerror', e => results.errors.push({ url: page.url(), error: e.message }));
  await login(page);
  await check('Registry filters, detail return and history', async () => {
    await page.goto(base + '/app/empresas/');
    await page.locator('#filtro-busca').fill('Pad');
    await page.waitForURL('**q=Pad');
    await page.locator('#filtro-busca').fill('Cl');
    await page.waitForURL('**q=Cl');
    await page.locator('tbody a').first().click();
    assert.equal(await page.getByRole('link', { name: 'Voltar às empresas' }).getAttribute('href'), '/app/empresas/?q=Cl');
    await page.getByRole('link', { name: 'Voltar às empresas' }).click();
    await page.locator('#filtro-busca').fill('semresultadoxyz');
    await page.waitForURL('**q=semresultadoxyz');
    assert(await page.getByText('Nenhuma empresa encontrada').isVisible());
    await page.goBack();
    await page.waitForFunction(() => document.querySelector('#filtro-busca')?.value === 'Cl');
  });
  await check('Mobile menu, modal focus, Escape and invalid form recovery', async () => {
    await page.goto(base + '/app/empresas/');
    await page.setViewportSize({ width: 390, height: 850 });
    await page.locator('[data-menu-toggle]').click();
    assert.equal(await page.locator('#mobile-nav [aria-current=page]').innerText(), 'Empresas');
    await page.keyboard.press('Escape');
    assert(await page.locator('[data-menu-toggle]').evaluate(e => e === document.activeElement));
    await page.locator('[data-modal-open=company-dialog]').first().click();
    assert(await page.locator('#company-dialog input:not([type=hidden])').first().evaluate(e => e === document.activeElement));
    await page.keyboard.press('Escape');
    assert(await page.locator('[data-modal-open=company-dialog]').first().evaluate(e => e === document.activeElement));
    await page.locator('[data-modal-open=company-dialog]').first().click();
    await page.locator('#company-dialog [name=name]').fill('Empresa de teste com erro');
    const cnpj = page.locator('#company-dialog [name=cnpj_masked]');
    if (await cnpj.count()) await cnpj.fill('123');
    await page.locator('#company-dialog form').evaluate(e => e.noValidate = true);
    await page.getByRole('button', { name: 'Salvar empresa', exact: true }).click();
    await page.locator('#company-dialog .field-error').waitFor();
    assert(await page.locator('#company-dialog').isVisible());
    assert.equal(await page.locator('#company-dialog [name=name]').inputValue(), 'Empresa de teste com erro');
    await page.keyboard.press('Escape');
  });
  await check('OFX company picker keyboard', async () => {
    await page.goto(base + '/app/conciliacao/');
    await page.getByRole('button', { name: 'Importar OFX', exact: true }).click();
    await page.locator('[data-company-search]').fill('Pad');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    assert(await page.locator('[data-company-picker] select').inputValue());
    assert(await page.locator('[data-company-search]').evaluate(e => e === document.activeElement));
    await page.keyboard.press('Escape');
    assert(await page.locator('#import-ofx').isHidden());
  });
  await check('Responsive shared shell and 200% reflow', async () => {
    const evidence = [];
    for (const width of [375, 768, 1024, 720]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(base + '/app/empresas/');
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      evidence.push({ width, overflow: false });
    }
    return { evidence, note: '720 CSS px = viewport reflow at 200% of 1440; native browser zoom not automated.' };
  });
  await check('Theme overrides system and persists on public/auth pages', async () => {
    const themed = await context(); const p = await themed.newPage();
    try {
      await p.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
      await p.goto(base + '/entrar/');
      await p.getByRole('button', { name: 'Claro', exact: true }).click();
      await p.waitForLoadState();
      assert.equal(await p.evaluate(() => getComputedStyle(document.documentElement).colorScheme), 'light');
      await p.goto(base + '/');
      assert.equal(await p.locator('html').getAttribute('data-theme'), 'light');
      await p.getByRole('button', { name: 'Sistema', exact: true }).click();
      await p.waitForLoadState();
      assert.equal(await p.evaluate(() => getComputedStyle(document.documentElement).colorScheme), 'dark');
      await p.emulateMedia({ colorScheme: 'light' });
      assert.equal(await p.evaluate(() => getComputedStyle(document.documentElement).colorScheme), 'light');
      await p.getByRole('button', { name: 'Escuro', exact: true }).click(); await p.reload();
      assert.equal(await p.evaluate(() => getComputedStyle(document.documentElement).colorScheme), 'dark');
    } finally { await themed.close(); }
  });
  const paths = ['/app/', '/app/empresas/', '/app/revisoes/', '/app/certificados/', '/app/nfse/', '/app/guias/', '/app/integra-contador/', '/app/integra-contador/dte/', '/app/integra-contador/parcelamentos/', '/app/conciliacao/', '/app/radar-reforma/', '/app/triagem/', '/app/triagem/caixas/', '/app/configuracao/', '/app/configuracoes/', '/app/equipe/', '/app/ia/'];
  await scan(page, paths, 'workspace');
  await ctx.close();
  for (const name of ['operador', 'auditor', 'rival', 'dev', 'suporte', 'comercial']) {
    const persona = await context(); const p = await persona.newPage(); p.setDefaultTimeout(8000);
    try {
      await login(p, name);
      await check('Persona ' + name, async () => {
        if (['dev','suporte','comercial'].includes(name)) {
          const response = await p.goto(base + '/platform/configuracoes/');
          assert.equal(response.status(), name === 'dev' ? 200 : 403);
          if (name === 'dev') {
            await p.goto(base + '/platform/tenants/');
            const tenant = await p.getByRole('link', { name: 'Escritório Demonstração', exact: true }).getAttribute('href');
            await scan(p, ['/platform/', '/platform/tenants/', '/platform/configuracoes/', tenant], 'platform');
          }
        } else {
          const response = await p.goto(base + '/app/empresas/');
          if (name === 'operador') { assert.equal(await p.locator('tbody tr').count(), 3); assert.equal(await p.locator('[data-modal-open=company-dialog]').count(), 0); }
          if (name === 'auditor') assert.equal(await p.locator('[data-modal-open=company-dialog]').count(), 0);
          if (name === 'rival') assert.equal(response.status(), 403);
        }
      });
    } finally { await persona.close(); }
  }
  const demo = await context(); const p = await demo.newPage(); p.setDefaultTimeout(8000);
  try {
    await p.goto(base + '/demo/'); await p.getByRole('button', { name: 'Iniciar demonstração fictícia' }).click();
    await check('Demo review complete and retained filter', async () => {
      await p.goto(base + '/app/revisoes/?q=Oficina');
      await p.locator('main a').filter({ hasText: 'Conferir e decidir' }).first().click();
      await p.locator('[name=accumulator_code]').fill('2005');
      await p.getByRole('button', { name: 'Registrar decisão conferida' }).click();
      assert(await p.getByText('Acumulador decidido', { exact: true }).isVisible());
      assert.equal(await p.getByRole('link', { name: 'Voltar à fila' }).getAttribute('href'), '/app/revisoes/?q=Oficina');
    });
    await check('Demo certificate and NFSe activation', async () => {
      await p.goto(base + '/app/certificados/'); await p.getByRole('button', { name: 'Simular certificado', exact: true }).click();
      const select = p.locator('[name=demo_company_id]'); await select.selectOption(await select.locator('option').nth(1).getAttribute('value'));
      await p.getByRole('button', { name: 'Registrar resultado fictício' }).click();
      assert(await p.locator('.flash-stack').count());
      await p.goto(base + '/app/nfse/'); await p.locator('[name=companies]').first().check();
      await p.getByRole('button', { name: 'Ativar coleta', exact: true }).click();
      assert.match(await p.locator('.flash-stack').innerText(), /fict|simulad/i);
    });
    await check('Demo guide emission and PDF', async () => {
      await p.goto(base + '/app/guias/'); await p.getByRole('button', { name: 'Simular emissão', exact: true }).first().click();
      await p.getByRole('button', { name: 'Gerar resultado fictício', exact: true }).click();
      const [download] = await Promise.all([p.waitForEvent('download'), p.getByRole('link', { name: 'Baixar PDF fictício sem validade' }).click()]);
      return { filename: download.suggestedFilename() };
    });
    await check('Demo parcelamento batch', async () => {
      await p.goto(base + '/app/integra-contador/parcelamentos/'); await p.locator('[name=selected_company]').first().check();
      await p.getByRole('button', { name: 'Consultar pedidos selecionados' }).click();
      assert.match(await p.locator('.flash-stack').innerText(), /concluída/);
    });
    await check('Demo reconciliation decision', async () => {
      await p.goto(base + '/app/conciliacao/'); await p.getByRole('button', { name: 'Comparar candidatos' }).click();
      await p.getByRole('button', { name: 'Confirmar correspondência fictícia' }).click();
      assert(await p.locator('.flash-stack').count());
    });
    await check('Demo archive review to download', async () => {
      await p.goto(base + '/app/triagem/'); await p.getByRole('link', { name: 'DOCUMENTO_FICTICIO_1.xml' }).click();
      await p.getByRole('button', { name: 'Aprovar para arquivamento' }).click();
      await p.getByRole('button', { name: 'Concluir arquivamento fictício' }).click();
      const [download] = await Promise.all([p.waitForEvent('download'), p.getByRole('link', { name: 'Baixar arquivo fictício' }).click()]);
      return { filename: download.suggestedFilename() };
    });
  } finally { await demo.close(); }
})().catch(error => { results.errors.push({ fatal: error.message }); process.exitCode = 1; })
  .finally(async () => {
    if (browser) await browser.close();
    fs.writeFileSync(`${output}/local-regression.json`, JSON.stringify(results, null, 2));
    console.log(JSON.stringify({ flows: results.flows.length, failed: results.flows.filter(x => x.status === 'failed'), screens: results.screens.length, visualIssues: results.screens.filter(x => x.overflow || x.h1.length !== 1 || x.unlabeled.length), errors: results.errors }));
    if (results.flows.some(x => x.status === 'failed') || results.errors.length) process.exitCode = 1;
  });
