const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const base = 'http://127.0.0.1:8011';
const output = '.playwright-mcp/nfse-inline-review';
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
      await page.goto(base + '/app/nfse/');
      assert.equal(await page.locator('[name="competence_month"]').inputValue(), '08');
      assert.equal(await page.locator('[name="competence_year"]').inputValue(), '2026');
      await page.goto(base + '/app/nfse/?status=unclassified');

      assert.equal(await page.getByRole('link', { name: /^Revisões/ }).count(), 0);
      assert.equal(await page.locator('a[href="/app/revisoes/"]').count(), 0);
      assert.deepEqual(
        await page.locator('#nfse-status option').allTextContents(),
        ['Todas', 'Classificadas', 'Não classificadas'],
      );
      assert((await page.locator('.nfse-company-group').count()) > 0);
      const editors = page.locator('.nfse-inline-review');
      assert((await editors.count()) > 0, 'review list must expose inline classification');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

      const firstEditor = editors.first();
      const input = firstEditor.locator('input[name="accumulator_code"]');
      const button = firstEditor.getByRole('button', { name: 'Classificar' });
      await input.focus();
      assert.equal(await input.evaluate(element => element.matches(':focus-visible')), true);
      const details = page.locator('.nfse-review-details').first();
      await details.locator('summary').click();
      assert.equal(await details.getByRole('link', { name: 'Baixar XML' }).count(), 1);
      assert((await details.locator('dt').count()) >= 4);

      if (viewport.width > 500) {
        const reviewedInputId = await input.getAttribute('id');
        const option = firstEditor.locator('datalist option').first();
        assert((await option.count()) > 0, 'inline review needs company-scoped accumulator options');
        await input.fill(await option.getAttribute('value'));
        await button.click();
        await page.waitForLoadState('networkidle');
        assert.match(page.url(), /\/app\/nfse\/\?status=unclassified/);
        assert.equal(await page.locator(`#${reviewedInputId}`).count(), 0);
      }

      await page.screenshot({ path: `${output}/notes-${viewport.width}.png`, fullPage: true });
      assert.deepEqual(errors, []);
      results.push({ viewport, inlineEditors: await page.locator('.nfse-inline-review').count() });
      await context.close();
    }
    fs.writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
