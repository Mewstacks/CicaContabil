const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const base = 'http://127.0.0.1:8011';
const output = '.playwright-mcp/tenant-detail';
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const results = { screens: [], errors: [] };
  try {
    for (const scenario of [
      { theme: 'light', width: 1440, height: 1000, reducedMotion: 'no-preference' },
      { theme: 'dark', width: 390, height: 844, reducedMotion: 'reduce' },
      { theme: 'system', width: 1024, height: 768, reducedMotion: 'no-preference' },
    ]) {
      const context = await browser.newContext({
        viewport: { width: scenario.width, height: scenario.height },
        reducedMotion: scenario.reducedMotion,
      });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        return url.origin === base || ['data:', 'blob:'].includes(url.protocol)
          ? route.continue()
          : route.abort();
      });
      await context.addCookies([{ name: 'hub_theme', value: scenario.theme, url: base }]);
      const page = await context.newPage();
      page.on('pageerror', error => results.errors.push(error.message));
      page.on('console', message => {
        if (message.type() === 'error') results.errors.push(message.text());
      });

      await page.goto(`${base}/entrar/`);
      await page.locator('[name=username]').fill('dev@hubcontador.local');
      await page.locator('[name=password]').fill('persona-local-password-123');
      await page.locator('button[type=submit]').first().click();
      await page.goto(`${base}/platform/tenants/`);
      await page.locator('.platform-row-link').first().click();
      await page.waitForLoadState('networkidle');

      const openInvite = page.getByRole('button', { name: 'Adicionar pessoa' });
      assert.equal(await openInvite.count(), 1);
      await openInvite.click();
      assert.equal(await page.locator('#invite-dialog').getAttribute('hidden'), null);
      assert.deepEqual(
        await page.locator('#id_invite-role option').evaluateAll(options =>
          options.map(option => option.textContent.trim()),
        ),
        ['Proprietário', 'Administrador', 'Gestor', 'Operador', 'Financeiro', 'Auditor'],
      );
      assert.equal(await page.locator('#id_invite-email').evaluate(element => element === document.activeElement), true);

      const facts = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        unlabeled: [...document.querySelectorAll('input:not([type=hidden]),select,textarea,button')]
          .filter(element => element.getClientRects().length && !element.closest('[hidden]'))
          .filter(element => !element.labels?.length && !element.getAttribute('aria-label') &&
            !element.getAttribute('aria-labelledby') && !element.textContent.trim())
          .map(element => element.id || element.name),
        active: document.activeElement?.id,
      }));
      assert.equal(facts.overflow, false);
      assert.deepEqual(facts.unlabeled, []);

      const file = `${output}/${scenario.theme}-${scenario.width}.png`;
      await page.screenshot({ path: file, fullPage: true });
      results.screens.push({ ...scenario, ...facts, file, url: page.url() });

      if (scenario.theme === 'light') {
        await page.locator('#invite-dialog form').evaluate(form => { form.noValidate = true; });
        await page.getByRole('button', { name: 'Enviar convite' }).click();
        await page.waitForLoadState('networkidle');
        const errorSummary = page.locator('#invite-dialog [data-form-errors]');
        await errorSummary.waitFor();
        assert.match(await errorSummary.textContent(), /Confira e-mail da pessoa/);
        assert.equal(await errorSummary.evaluate(element => element === document.activeElement), true);
        assert.equal(await page.locator('#id_invite-email').getAttribute('aria-invalid'), 'true');
        await page.screenshot({ path: `${output}/validation-error-1440.png`, fullPage: true });
      }

      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#invite-dialog').getAttribute('hidden'), '');
      assert.equal(await openInvite.evaluate(element => element === document.activeElement), true);
      await context.close();
    }
    assert.deepEqual(results.errors, []);
    fs.writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
