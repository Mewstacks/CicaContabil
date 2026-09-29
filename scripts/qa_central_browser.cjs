/* Synthetic, local-only central review. Start QA_REVIEW_SUITE=central first. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const base = 'http://127.0.0.1:8012';
const fixture = JSON.parse(fs.readFileSync('.tmp/central-review/central-session.json'));
const output = '.playwright-mcp/central-review';
fs.mkdirSync(output, { recursive: true });
const results = { screens: [], checks: [], errors: [] };
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, executablePath: process.env.QA_BROWSER_EXECUTABLE });
  for (const role of ['operator', 'owner', 'auditor']) {
    const context = await browser.newContext();
    try {
      await context.route('**/*', route => new URL(route.request().url()).origin === base
        ? route.continue() : route.abort());
      await context.addCookies([{ name: 'sessionid', value: fixture.cookies[role], url: base }]);
      const page = await context.newPage();
      page.on('pageerror', error => results.errors.push(error.message));
      page.on('console', msg => {
        if (msg.type() === 'error' && msg.location().url !== base + fixture.activities.restricted)
          results.errors.push({ text: msg.text(), url: msg.location().url });
      });
      await page.goto(base + '/app/');
      const skipTour = page.getByRole('button', { name: 'Pular', exact: true });
      if (await skipTour.isVisible()) await skipTour.click();
      const paths = [
        '/app/',
        '/app/?view=portfolio',
        '/app/?filter=blocked',
        fixture.activities.today,
        fixture.activities.guide,
        fixture.company_detail,
      ];
      if (role === 'owner') paths.push('/app/?view=management', '/app/atividades/modelos/');
      for (const theme of ['light', 'dark']) {
        await context.addCookies([{ name: 'hub_theme', value: theme, url: base }]);
        for (const width of [1440, 390]) {
          await page.setViewportSize({ width, height: 960 });
          for (const [index, path] of paths.entries()) {
            const response = await page.goto(base + path);
            assert.equal(response.status(), 200, `${role} ${path}`);
            const facts = await page.evaluate(() => ({
              overflow: document.documentElement.scrollWidth > innerWidth,
              headings: [...document.querySelectorAll('h1,h2')].map(e => e.textContent.trim()),
            }));
            const file = `${output}/${role}-${theme}-${width}-${index}.png`;
            await page.screenshot({ path: file, fullPage: true });
            results.screens.push({ role, theme, width, path, file, ...facts });
            assert.equal(facts.overflow, false, `Overflow: ${file}`);
            if (path === '/app/' && role === 'operator') {
              const agenda = await page.getByRole('region', { name: 'Agenda de atividades' }).innerText();
              for (const title of ['QA tarefa atrasada', 'QA tarefa de hoje', 'QA tarefa futura']) assert.ok(agenda.includes(title));
              for (const title of ['QA tarefa compartilhada', 'QA tarefa de outra pessoa', 'QA tarefa fora da carteira']) assert.ok(!agenda.includes(title));
              results.checks.push('Personal agenda excludes other assignees and unassigned tasks');
            }
            if (path.includes('view=portfolio') && role === 'operator') {
              const agenda = await page.getByRole('region', { name: 'Agenda de atividades' }).innerText();
              assert.ok(agenda.includes('QA tarefa compartilhada'));
              assert.ok(agenda.includes('QA tarefa de outra pessoa'));
              assert.ok(!agenda.includes('QA tarefa fora da carteira'));
              results.checks.push('Portfolio includes authorized shared work only');
            }
            if (role === 'auditor' && path === fixture.activities.today) {
              assert.equal(await page.getByRole('button', { name: 'Concluir atividade', exact: true }).count(), 0);
              results.checks.push('Auditor has no completion control');
            }
            if (role === 'operator' && path === fixture.activities.guide) {
              await assert.equal(
                await page.getByRole('link', { name: 'Abrir guia', exact: true }).count(),
                1,
              );
              await assert.equal(
                await page.getByText('Guia disponível', { exact: true }).count(),
                1,
              );
              results.checks.push('Guide outcome exposes source action and payment state');
            }
            if (path === fixture.company_detail) {
              const rows = await page.locator('#atividades tbody tr').allTextContents();
              assert.ok(rows.findIndex(row => row.includes('QA ficha prazo legal')) < rows.findIndex(row => row.includes('QA ficha prazo interno')));
              results.checks.push(`${role}: company activity list follows the effective due date`);
            }
            if (role === 'owner' && path === '/app/atividades/modelos/') {
              assert.equal(await page.getByRole('heading', { name: 'Modelos de atividades' }).count(), 1);
              results.checks.push('Administrator can inspect recurring activity models');
            }
          }
        }
      }
      if (role !== 'owner') {
        const response = await page.goto(base + fixture.activities.restricted);
        assert.equal(response.status(), 404);
        results.checks.push(`${role}: other portfolio activity refused`);
      }
      if (role === 'owner') {
        for (const width of [1440, 390]) {
          await page.setViewportSize({ width, height: 960 });
          const response = await page.goto(base + `/app/configuracao/?source=${fixture.disabled_source_id}`);
          assert.equal(response.status(), 200, `owner setup ${width}`);
          const checkbox = page.getByRole('checkbox', {
            name: 'Entendo que preciso executar uma nova sincronização antes de usar estes dados.',
          });
          assert.equal(await checkbox.count(), 1);
          await checkbox.focus();
          assert.equal(await checkbox.evaluate(element => document.activeElement === element), true);
          const facts = await page.evaluate(() => ({
            overflow: document.documentElement.scrollWidth > innerWidth,
            source: document.querySelector('.setup-source-reactivation')?.textContent?.trim() || '',
          }));
          assert.equal(facts.overflow, false, `Setup overflow ${width}`);
          assert.ok(facts.source.includes('Reativar fonte'));
          const file = `${output}/owner-setup-${width}.png`;
          await page.screenshot({ path: file, fullPage: true });
          results.screens.push({ role, theme: 'light', width, path: '/app/configuracao/', file, ...facts });
        }
        results.checks.push('Owner setup exposes an explicit, keyboard-focusable source reactivation control');
      }
      if (role === 'operator') {
        await page.setViewportSize({ width: 1440, height: 960 });
        const missingEvidence = await page.goto(base + fixture.activities['needs-evidence']);
        assert.equal(missingEvidence.status(), 200);
        await Promise.all([
          page.waitForURL(url => url.pathname === fixture.activities['needs-evidence']),
          page.getByRole('button', { name: 'Concluir atividade', exact: true }).click(),
        ]);
        const incompleteFacts = await page.evaluate(() => ({
          status: document.querySelector('.activity-status')?.textContent?.trim(),
          message: document.querySelector('.flash-stack .flash')?.textContent || '',
        }));
        assert.notEqual(incompleteFacts.status, 'Concluída', 'Missing evidence must not complete activity');
        assert.ok(incompleteFacts.message.includes('exige'), 'Missing evidence feedback must be visible');
        assert.equal(await page.getByRole('button', { name: 'Concluir atividade', exact: true }).count(), 1);
        results.checks.push('Completion without evidence remains open and explains the requirement');
        const detail = await page.goto(base + fixture.activities['complete-v2']);
        assert.equal(detail.status(), 200);
        const evidence = page.locator('textarea[name="summary"]');
        await evidence.focus();
        const evidenceFocus = await evidence.evaluate(element => ({
          focused: element === document.activeElement,
          outlineStyle: getComputedStyle(element).outlineStyle,
          outlineWidth: getComputedStyle(element).outlineWidth,
        }));
        assert.ok(
          evidenceFocus.focused && evidenceFocus.outlineStyle !== 'none' && evidenceFocus.outlineWidth !== '0px',
          'Evidence control needs visible keyboard focus',
        );
        await page.locator('input[name="reference"]').fill('QA-LOCAL-001');
        await evidence.fill('Conferência sintética registrada pelo operador QA.');
        await Promise.all([
          page.waitForURL(url => url.pathname === fixture.activities['complete-v2']),
          page.getByRole('button', { name: 'Registrar evidência', exact: true }).click(),
        ]);
        assert.equal(
          await page.getByText('Evidência registrada na trilha da atividade.', { exact: true }).count(),
          1,
        );
        assert.ok(
          await page.getByText('Conferência sintética registrada pelo operador QA.', { exact: true }).count() >= 1,
          'Evidence summary must be visible in its local trail',
        );
        await Promise.all([
          page.waitForURL(url => url.pathname === fixture.activities['complete-v2']),
          page.getByRole('button', { name: 'Concluir atividade', exact: true }).click(),
        ]);
        assert.equal(
          await page.getByText('Atividade concluída com a evidência registrada.', { exact: true }).count(),
          1,
        );
        assert.equal(await page.getByText('Concluída', { exact: true }).count(), 1);
        assert.equal(await page.getByRole('button', { name: 'Concluir atividade', exact: true }).count(), 0);
        assert.equal(await page.getByText('Atividade encerrada.', { exact: true }).count(), 1);
        await page.setViewportSize({ width: 390, height: 960 });
        const completedFacts = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          status: document.querySelector('.activity-detail-head')?.textContent?.includes('Concluída'),
        }));
        assert.equal(completedFacts.overflow, false, 'Completed detail has mobile overflow');
        assert.ok(completedFacts.status, 'Completed state stays visible on mobile');
        await page.screenshot({ path: `${output}/operator-completed-mobile.png`, fullPage: true });
        await page.goto(base + '/app/');
        const personalAgenda = await page.getByRole('region', { name: 'Agenda de atividades' }).innerText();
        assert.ok(!personalAgenda.includes('QA tarefa para concluir'));
        results.checks.push({ operatorEvidenceCompletion: evidenceFocus });
      }
      await page.goto(base + '/app/');
      const summary = page.locator('.closing-row summary').nth(1);
      await summary.focus();
      await page.keyboard.press('Enter');
      assert.equal(await summary.locator('..').getAttribute('open'), '');
      const focus = await summary.evaluate(element => ({
        focused: element === document.activeElement,
        outlineStyle: getComputedStyle(element).outlineStyle,
        outlineWidth: getComputedStyle(element).outlineWidth,
      }));
      assert.ok(focus.focused && focus.outlineStyle !== 'none' && focus.outlineWidth !== '0px');
      results.checks.push({ role, keyboardClosingDetails: focus });
      await page.screenshot({ path: `${output}/${role}-keyboard-closing.png`, fullPage: true });
    } finally { await context.close(); }
  }
})().catch(error => { results.failure = error.stack; process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  fs.writeFileSync(`${output}/results.json`, JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ screens: results.screens.length, checks: results.checks.length, errors: results.errors, failure: results.failure }));
});
