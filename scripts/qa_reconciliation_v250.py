"""Rendered QA for the exception-first reconciliation pass (V-250).

Requires ``scripts/qa_ui_server.py`` on port 8011 with the synthetic non-demo
reconciliation fixture prepared by the task. The browser is always closed.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8011"
MAPPING_SOURCE = "82f0ef48-8197-4ed7-8d40-76b54e78d08b"
OUTPUT = Path(".playwright-mcp/reconciliation-v250")
OUTPUT.mkdir(parents=True, exist_ok=True)
results: dict[str, object] = {"screens": [], "checks": [], "errors": []}


def record_check(name: str) -> None:
    checks = results["checks"]
    assert isinstance(checks, list)
    checks.append(name)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    try:
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()
        page.on(
            "pageerror",
            lambda error: results["errors"].append(f"pageerror: {error}"),  # type: ignore[union-attr]
        )
        page.on(
            "console",
            lambda message: (
                results["errors"].append(f"console {message.type}: {message.text}")  # type: ignore[union-attr]
                if message.type == "error"
                else None
            ),
        )
        page.goto(f"{BASE}/entrar/")
        page.locator("[name=username]").fill("demo@hubcontador.local")
        page.locator("[name=password]").fill("persona-local-password-123")
        page.locator("button[type=submit]").first.click()
        page.wait_for_load_state()
        page.goto(f"{BASE}/app/")
        page.locator('[data-popover-toggle="office-list"]').click()
        page.locator('#office-list button:has-text("Escritório QA")').click()
        page.wait_for_load_state()

        response = page.goto(f"{BASE}/app/conciliacao/")
        assert response is not None and response.status == 200
        assert (
            page.locator("#reconciliation-next-action-title").inner_text().startswith("Resolver 1")
        )
        assert page.get_by_role("link", name="Revisar conflitos").count() == 1
        assert (
            page.locator(".reconciliation-v2-overview .reconciliation-metrics article").count() == 4
        )
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=OUTPUT / "overview-desktop.png", full_page=True)
        record_check("desktop overview prioritizes the conflict and has no horizontal overflow")

        page.get_by_role("link", name="Revisar conflitos").click()
        page.wait_for_selector("#movimentos:not([hidden])")
        assert page.locator('#movimentos input[name="movement_ids"]').count() == 1
        record_check("next action opens the filtered exception queue")

        page.goto(f"{BASE}/app/conciliacao/?movement_review=invented#movimentos")
        page.wait_for_selector(".reconciliation-filter-error")
        assert page.locator('#movimentos input[name="movement_ids"]').count() == 0
        assert (
            "Nenhum movimento foi exibido"
            in page.locator(".reconciliation-filter-error").inner_text()
        )
        record_check(
            "invalid explicit filter shows a recovery path and never broadens the portfolio"
        )

        mapping_url = f"{BASE}/app/conciliacao/arquivos/{MAPPING_SOURCE}/mapear/"
        page.goto(mapping_url)
        assert page.locator(".reconciliation-mapping-intro > div").count() == 3
        assert page.locator("#map-date").input_value() == ""
        page.locator("#map-date").select_option("MovimentoData")
        page.locator("#map-description").select_option("Narrativa")
        page.locator("#map-amount").select_option("MovimentoValor")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=OUTPUT / "mapping-desktop.png", full_page=True)

        page.locator("#layout-name").fill("")
        page.locator("#map-description").select_option("")
        page.locator("#map-debit").select_option("Referencia")
        with page.expect_navigation():
            page.locator(".reconciliation-mapping-form").evaluate(
                "form => HTMLFormElement.prototype.submit.call(form)"
            )
        summary = page.locator("[data-error-summary]")
        summary.wait_for()
        assert summary.evaluate("node => node === document.activeElement")
        assert page.locator("#map-amount").input_value() == "MovimentoValor"
        assert page.locator("#map-debit").input_value() == "Referencia"
        assert page.locator("#map-description").input_value() == ""
        record_check(
            "server validation preserves every mapping choice and focuses its linked summary"
        )

        page.set_viewport_size({"width": 375, "height": 812})
        page.emulate_media(color_scheme="dark", reduced_motion="reduce")
        page.goto(mapping_url)
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        small_targets = page.locator(
            ".reconciliation-mapping-page button, .reconciliation-mapping-page a[href], "
            ".reconciliation-mapping-page input, .reconciliation-mapping-page select"
        ).evaluate_all(
            "nodes => nodes.filter(node => node.getClientRects().length)"
            ".map(node => ({name: node.textContent.trim() || node.name, "
            "h: node.getBoundingClientRect().height}))"
            ".filter(item => item.h > 0 && item.h < 24)"
        )
        assert small_targets == [], small_targets
        page.locator("#layout-name").focus()
        assert page.locator("#layout-name").evaluate("node => node === document.activeElement")
        page.screenshot(path=OUTPUT / "mapping-mobile-dark.png", full_page=True)
        record_check(
            "mobile dark/reduced-motion mapping has visible focus, safe targets and no overflow"
        )

        screens = results["screens"]
        assert isinstance(screens, list)
        screens.extend(
            [
                str(OUTPUT / "overview-desktop.png"),
                str(OUTPUT / "mapping-desktop.png"),
                str(OUTPUT / "mapping-mobile-dark.png"),
            ]
        )
        context.close()
    finally:
        browser.close()

(OUTPUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")
print(json.dumps(results, ensure_ascii=False))
