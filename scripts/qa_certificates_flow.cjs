const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const base = 'http://127.0.0.1:8011';
const output = '.playwright-mcp/certificates-review';
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const results = [];
  try {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        return url.origin === base ? route.continue() : route.abort();
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.goto(base + '/entrar/');
      await page.locator('[name=username]').fill('demo@hubcontador.local');
      await page.locator('[name=password]').fill('persona-local-password-123');
      await page.getByRole('button', { name: 'Entrar' }).click();
      await page.goto(base + '/app/certificados/');
      const modal = page.locator('#certificate-dialog');
      assert.equal(await modal.isHidden(), true, 'modal must not open on page load');
      assert.equal(await page.locator('#empresas-sem-certificado').count(), 1);
      assert.equal(await page.locator('#certificados-cadastrados').count(), 1);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

      await page.getByRole('button', { name: 'Importar certificados' }).click();
      await page.locator('[name=pfx_files]').setInputFiles({
        name: 'Cliente Exemplo - 1234.pfx', mimeType: 'application/x-pkcs12', buffer: Buffer.from('invalid'),
      });
      await page.route('**/app/certificados/', async route => {
        if (route.request().method() === 'POST') {
          await route.fulfill({ status: 500, contentType: 'text/html', body: '<!doctype html><title>erro</title>' });
        } else await route.continue();
      });
      await page.getByRole('button', { name: 'Importar e vincular' }).click();
      const retry = page.locator('[data-certificate-queue-retry]');
      await retry.waitFor({ state: 'visible' });
      assert.match(await retry.textContent(), /Cliente Exemplo - 1234\.pfx/);
      assert.match(await retry.textContent(), /serviço oscilou/i);
      assert.doesNotMatch(await modal.textContent(), /Unexpected token|<!doctype/i);
      const modalBox = await page.locator('.certificate-import-dialog').boundingBox();
      const retryBox = await retry.boundingBox();
      assert(modalBox && retryBox && retryBox.y >= modalBox.y && retryBox.y < modalBox.y + modalBox.height);
      await page.getByRole('button', { name: 'Cancelar fila' }).click();
      assert.match(await page.locator('[data-certificate-queue-status]').textContent(), /cancelada/i);
      await page.locator('[data-modal-close]').first().click();
      assert.equal(await modal.isHidden(), true);
      await page.screenshot({ path: `${output}/certificates-${viewport.width}.png`, fullPage: true });

      let retryRequests = 0;
      await page.route('**/app/nfse/fila/repetir/', route => {
        retryRequests += 1;
        return route.fulfill({ status: 200, contentType: 'application/json', body: '{"changed":1}' });
      });
      await page.route('**/app/nfse/fila/', route => route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          counts: { queued: 1, running: 1, done: 1, attention: 1, skipped: 1 },
          updated_at: new Date().toISOString(),
          items: [
            { company: 'Alfa Serviços Ltda.', state: 'running', label: 'Coletando agora', detail: 'Consultando novas NFS-e desta empresa.', updated_at: new Date().toISOString() },
            { company: 'Beta Comércio Ltda.', state: 'queued', label: 'Na fila', detail: 'Primeira coleta aguardando processamento.', updated_at: null },
            { company: 'Gama Indústria Ltda.', state: 'done', label: 'Concluída', detail: '18 documentos na última coleta.', updated_at: new Date().toISOString() },
            { company_id: '00000000-0000-0000-0000-000000000004', company: 'Delta Consultoria Ltda.', state: 'failed', label: 'Falhou', detail: 'Revise a configuração desta empresa.', updated_at: new Date().toISOString() },
            { company: 'Épsilon Participações Ltda.', state: 'skipped', label: 'Ignorada', detail: 'Sem A1 válido; as outras empresas continuam.', updated_at: null },
          ],
        }),
      }));
      await page.goto(base + '/app/nfse/?view=collection');
      const liveQueue = page.locator('[data-nfse-live-queue]');
      await liveQueue.waitFor({ state: 'visible' });
      await page.waitForFunction(() => document.querySelector('[data-nfse-queue-list]')?.getAttribute('aria-busy') === 'false');
      assert.equal(await liveQueue.getByText('Fila de coleta').count(), 1);
      assert((await page.locator('.nfse-queue-item').count()) > 0, 'live queue must list companies');
      assert.equal(await liveQueue.getByText('Coletando agora', { exact: true }).count(), 1);
      assert.equal(await liveQueue.getByText('Concluída', { exact: true }).count(), 1);
      assert.equal(await liveQueue.getByText('Ignorada', { exact: true }).count(), 1);
      await liveQueue.getByRole('button', { name: 'Tentar novamente' }).click();
      await page.waitForTimeout(100);
      assert.equal(retryRequests, 1);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      const scrollBeforeRefresh = await page.evaluate(() => {
        window.scrollTo(0, Math.min(700, document.documentElement.scrollHeight - innerHeight));
        return window.scrollY;
      });
      await page.waitForTimeout(5500);
      const scrollAfterRefresh = await page.evaluate(() => window.scrollY);
      assert(Math.abs(scrollAfterRefresh - scrollBeforeRefresh) < 2, 'live refresh must preserve page scroll');
      await page.screenshot({ path: `${output}/nfse-queue-${viewport.width}.png`, fullPage: true });
      const unexpectedErrors = errors.filter(message => !message.includes('status of 500'));
      results.push({ viewport, errors, unexpectedErrors, modalClosed: await modal.isHidden() });
      assert.deepEqual(unexpectedErrors, []);
      await context.close();
    }
    fs.writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
