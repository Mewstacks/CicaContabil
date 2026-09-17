/* Isolated Playwright check for the reconciliation configuration and review screens.
 * Requires scripts/qa_ui_server.py on 127.0.0.1:8011. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const base = 'http://127.0.0.1:8011';
const output = '.playwright-mcp/ui-review';
const results = { screens: [], checks: [], errors: [] };

async function login(page) {
  await page.goto(`${base}/entrar/`);
  await page.locator('[name=username]').fill('demo@hubcontador.local');
  await page.locator('[name=password]').fill('persona-local-password-123');
  await page.locator('button[type=submit]').first().click();
  await page.waitForLoadState();
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      return url.origin === base ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(10_000);
    page.on('pageerror', error => results.errors.push({ url: page.url(), error: error.message }));
    page.on('console', message => {
      const expectedValidationResponse = (
        page.url() === `${base}/app/conciliacao/importar/`
        && message.text().includes('server responded with a status of 400')
      );
      if (message.type() === 'error' && !expectedValidationResponse) {
        results.errors.push({ url: page.url(), error: message.text() });
      }
    });
    await login(page);

    for (const theme of ['light', 'dark']) {
      await context.addCookies([{ name: 'hub_theme', value: theme, url: base }]);
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 960 });
        const response = await page.goto(`${base}/app/conciliacao/configuracao/`);
        assert.equal(response.status(), 200);
        await page.locator('#configuracao').waitFor();
        const facts = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          headings: [...document.querySelectorAll('h1')].map(node => node.textContent.trim()),
          unlabeled: [...document.querySelectorAll('input:not([type=hidden]),select,textarea')]
            .filter(node => node.getClientRects().length && !node.getAttribute('aria-label'))
            .filter(node => !node.id || !document.querySelector(`label[for="${CSS.escape(node.id)}"]`))
            .map(node => node.id || node.name),
          targets: [...document.querySelectorAll('button,a[href],input,select')]
            .filter(node => node.getClientRects().length)
            .filter(node => {
              const rect = node.getBoundingClientRect();
              return rect.width > 0 && rect.height > 0 && rect.height < 32;
            }).map(node => node.textContent.trim() || node.getAttribute('aria-label') || node.name),
        }));
        assert.equal(facts.overflow, false);
        assert.deepEqual(facts.headings, ['Configuração da conciliação']);
        assert.deepEqual(facts.unlabeled, []);
        const screenshot = `${output}/reconciliation-config-${theme}-${width}.png`;
        await page.screenshot({ path: screenshot, fullPage: true });
        results.screens.push({ theme, width, status: response.status(), ...facts, screenshot });
      }
    }

    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto(`${base}/app/conciliacao/configuracao/`);
    const accountsLink = page.locator('a[href="#plano-contas"]').first();
    await accountsLink.focus();
    assert(await accountsLink.evaluate(node => node === document.activeElement));
    await page.locator('#contas-financeiras form').evaluate(form => { form.noValidate = true; });
    await page.locator('#contas-financeiras button[type=submit]').click();
    await page.locator('#contas-financeiras [data-form-errors]').waitFor();
    assert(await page.locator('#contas-financeiras [data-form-errors]').evaluate(node => node === document.activeElement));
    results.checks.push({ name: 'validation error retains page and moves focus to summary', status: 'passed' });

    await page.goto(`${base}/app/conciliacao/`);
    await page.setViewportSize({ width: 1440, height: 960 });
    const overviewFacts = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > innerWidth,
      metrics: document.querySelectorAll('.reconciliation-v2-overview .reconciliation-metrics article').length,
    }));
    assert.equal(overviewFacts.overflow, false);
    assert.equal(overviewFacts.metrics, 6);
    const desktopOverviewScreenshot = `${output}/reconciliation-overview-desktop.png`;
    await page.screenshot({ path: desktopOverviewScreenshot, fullPage: true });
    results.screens.push({ theme: 'dark', width: 1440, state: 'overview', screenshot: desktopOverviewScreenshot });
    assert.equal(await page.locator('#movimentos').count(), 1);
    assert.equal(await page.locator('#exportacoes').count(), 1);
    assert.equal(await page.locator('#reconciliation-upload-dialog').isVisible(), false);
    await page.getByRole('button', { name: 'Nova importação' }).first().click();
    const uploadDialog = page.locator('#reconciliation-upload-dialog');
    await uploadDialog.waitFor();
    assert(await uploadDialog.isVisible());
    assert(await uploadDialog.locator('.reconciliation-dropzone').isVisible());
    const companySelect = uploadDialog.locator('select[name=company]');
    const accountSelect = uploadDialog.locator('[data-financial-account-select]');
    await companySelect.selectOption({ index: 1 });
    const visibleAccounts = await accountSelect.locator('option:not([hidden])').evaluateAll(options => options.length);
    assert(visibleAccounts >= 1);
    const incompatibleAccountsStillVisible = await accountSelect.locator('option[data-company-id]').evaluateAll(
      (options, selectedCompany) => options.filter(option => (
        option.dataset.companyId !== selectedCompany && !option.hidden
      )).length,
      await companySelect.inputValue(),
    );
    assert.equal(incompatibleAccountsStillVisible, 0);
    const desktopUploadScreenshot = `${output}/reconciliation-upload-desktop.png`;
    await page.screenshot({ path: desktopUploadScreenshot, fullPage: true });
    results.screens.push({ theme: 'dark', width: 1440, state: 'upload-dialog', screenshot: desktopUploadScreenshot });
    await uploadDialog.getByRole('button', { name: 'Fechar envio de arquivos' }).click();
    const tab = page.locator('[data-reconciliation-tab][href="#movimentos"]');
    await tab.click();
    assert(await page.locator('#movimentos').isVisible());
    assert.equal(await page.locator('#visao-geral').isVisible(), false);
    await page.locator('[data-reconciliation-tab][href="#visao-geral"]').click();
    await page.setViewportSize({ width: 390, height: 900 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const mobileOverviewScreenshot = `${output}/reconciliation-overview-mobile.png`;
    await page.screenshot({ path: mobileOverviewScreenshot, fullPage: true });
    results.screens.push({ theme: 'dark', width: 390, state: 'overview', screenshot: mobileOverviewScreenshot });
    await page.getByRole('button', { name: 'Nova importação' }).first().click();
    const mobileUploadScreenshot = `${output}/reconciliation-upload-mobile.png`;
    await page.screenshot({ path: mobileUploadScreenshot, fullPage: true });
    results.screens.push({ theme: 'dark', width: 390, state: 'upload-dialog', screenshot: mobileUploadScreenshot });
    results.checks.push({ name: 'overview uses local tabs and a focused import dialog', status: 'passed' });

    const emptyUpload = uploadDialog.locator('.reconciliation-upload-form');
    await emptyUpload.locator('select[name=company]').selectOption({ index: 1 });
    await emptyUpload.locator('select[name=origin]').selectOption('bank_statement');
    await emptyUpload.locator('input[name=period_start]').fill('2026-09-01');
    await emptyUpload.locator('input[name=period_end]').fill('2026-09-30');
    await emptyUpload.evaluate(form => { form.noValidate = true; });
    const invalidUploadResponse = page.waitForResponse(response => (
      response.url() === `${base}/app/conciliacao/importar/`
      && response.request().method() === 'POST'
    ));
    await emptyUpload.locator('button[type=submit]').click();
    assert.equal((await invalidUploadResponse).status(), 400);
    const uploadErrors = page.locator('.reconciliation-upload-form [data-form-errors]');
    await uploadErrors.waitFor();
    assert(await uploadErrors.evaluate(node => node === document.activeElement));
    results.checks.push({ name: 'invalid upload retains the assistant and moves focus to its error summary', status: 'passed' });

    await page.goto(`${base}/app/conciliacao/`);

    // Exercise the browser path that a bookkeeper uses: submit one real CSV,
    // then confirm its generated processing can be opened in the mapper.
    await page.getByRole('button', { name: 'Nova importação' }).first().click();
    const upload = page.locator('#reconciliation-upload-dialog .reconciliation-upload-form');
    const filename = `qa-reconciliation-${Date.now()}.csv`;
    await upload.locator('select[name=company]').selectOption({ index: 1 });
    await upload.locator('select[name=origin]').selectOption('bank_statement');
    await upload.locator('input[name=period_start]').fill('2026-09-01');
    await upload.locator('input[name=period_end]').fill('2026-09-30');
    await upload.locator('input[name=files]').setInputFiles({
      name: filename,
      mimeType: 'text/csv',
      buffer: Buffer.from([
        'Data;Descricao;Valor;Documento',
        `2026-09-01;Recebimento QA;120,50;${filename}`,
      ].join('\n')),
    });
    assert(await upload.locator('.reconciliation-file-feedback').innerText().then(text => text.includes(filename)));
    const invalidUploadFields = await upload.locator(':invalid').evaluateAll(nodes => nodes.map(node => node.name));
    assert.deepEqual(invalidUploadFields, []);
    const uploadResponse = page.waitForResponse(response => (
      response.url() === `${base}/app/conciliacao/importar/`
      && response.request().method() === 'POST'
    ));
    await upload.locator('button[type=submit]').click();
    assert.equal((await uploadResponse).status(), 302);
    await page.waitForURL(`${base}/app/conciliacao/`);
    await page.locator('[data-reconciliation-tab][href="#processamentos"]').click();
    const mappingLink = page.getByRole('link', { name: 'Mapear' }).first();
    assert(
      await mappingLink.count(),
      `No mapping action after ${filename}: ${await page.locator('#processamentos').innerText()}`,
    );
    await mappingLink.waitFor();
    await mappingLink.click();
    await page.locator('.reconciliation-mapping-form').waitFor();
    assert(await page.locator('#map-date').inputValue());
    assert(await page.locator('#map-description').inputValue());
    assert(await page.locator('#map-amount').inputValue());
    const mappingResponse = page.waitForResponse(response => (
      response.url().includes('/app/conciliacao/arquivos/')
      && response.url().endsWith('/mapear/')
      && response.request().method() === 'POST'
    ));
    await page.locator('.reconciliation-mapping-form button[type=submit]').click();
    assert.equal((await mappingResponse).status(), 302);
    await page.waitForURL(`${base}/app/conciliacao/`);
    await page.locator('[data-reconciliation-tab][href="#movimentos"]').click();
    assert(await page.locator('#movimentos').innerText().then(text => text.includes('Recebimento QA')));
    results.checks.push({ name: 'CSV upload, inferred mapping and normalized review row complete in the browser', status: 'passed' });

    const movementDetail = page.getByRole('link', { name: 'Conferir' }).first();
    await movementDetail.click();
    await page.locator('.reconciliation-detail-grid').waitFor();
    assert(await page.locator('.reconciliation-allocation-summary').isVisible());
    await page.getByRole('link', { name: 'Voltar' }).click();
    await page.locator('#movimentos').waitFor();
    results.checks.push({ name: 'movement detail exposes evidence and allocation review', status: 'passed' });

    await page.getByRole('button', { name: 'Nova importação' }).first().click();
    const ofxUpload = page.locator('#reconciliation-upload-dialog .reconciliation-upload-form');
    const ofxId = `qa-ofx-${Date.now()}`;
    await ofxUpload.locator('select[name=company]').selectOption({ index: 1 });
    await ofxUpload.locator('select[name=origin]').selectOption('bank_statement');
    await ofxUpload.locator('input[name=period_start]').fill('2026-09-01');
    await ofxUpload.locator('input[name=period_end]').fill('2026-09-30');
    await ofxUpload.locator('input[name=files]').setInputFiles({
      name: `${ofxId}.ofx`,
      mimeType: 'application/x-ofx',
      buffer: Buffer.from(
        `OFXHEADER:100\n<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKACCTFROM><BANKID>001<ACCTID>123</BANKACCTFROM><BANKTRANLIST><STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260912<TRNAMT>-12.34<FITID>${ofxId}<NAME>Fornecedor OFX QA</STMTTRN></BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>`,
      ),
    });
    const ofxResponse = page.waitForResponse(response => (
      response.url() === `${base}/app/conciliacao/importar/`
      && response.request().method() === 'POST'
    ));
    await ofxUpload.locator('button[type=submit]').click();
    assert.equal((await ofxResponse).status(), 302);
    await page.waitForURL(`${base}/app/conciliacao/`);
    await page.locator('[data-reconciliation-tab][href="#movimentos"]').click();
    assert(await page.locator('#movimentos').innerText().then(text => text.includes('Fornecedor OFX QA')));
    results.checks.push({ name: 'OFX upload creates a normalized movement in the browser', status: 'passed' });
    await context.close();
  } catch (error) {
    results.errors.push({ fatal: error.message });
    process.exitCode = 1;
  } finally {
    await browser.close();
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(`${output}/reconciliation-ui.json`, JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  }
})();
