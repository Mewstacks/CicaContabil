"""Read-only browser checks for the local Regaro marketing page."""
from pathlib import Path
from tempfile import gettempdir
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8044/'
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(URL, wait_until='networkidle')
    assert page.locator('body').get_attribute('data-regaro-build') == 'spatial-v6'
    assert page.locator('#simulador').count() == 0
    assert '14 dias' in page.locator('.hero .fine').inner_text()
    page.keyboard.press('Tab')
    assert page.locator('.skip').evaluate('(e) => e === document.activeElement')
    assert page.locator('.skip').evaluate('(e) => getComputedStyle(e).outlineStyle') != 'none'
    page.keyboard.press('Enter')
    for scenario in ['guias', 'banco', 'documentos']:
        page.locator(f'[data-scenario={scenario}]').click()
        page.locator('#open-evidence').click()
        assert page.locator('#evidence-dialog').is_visible()
        assert page.locator('#evidence-source').inner_text()
        page.keyboard.press('Escape')
        assert not page.locator('#evidence-dialog').is_visible()
        assert page.locator('#open-evidence').evaluate('(e) => e === document.activeElement')
    assert page.locator('#motion-toggle, .scene-controls').count() == 0
    assert page.locator('.hero-answer').is_visible()
    for width, height, label in [(1440,1000,'desktop'),(390,844,'mobile'),(320,700,'small'),(768,1024,'tablet')]:
        page.set_viewport_size({'width':width,'height':height})
        page.goto(URL, wait_until='networkidle')
        page.evaluate('Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{})))')
        if not page.evaluate('document.documentElement.scrollWidth <= innerWidth'):
            print(page.evaluate("Array.from(document.querySelectorAll('*')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>[e.tagName,e.className,e.getBoundingClientRect().right])"))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label
        page.screenshot(path=str(Path(gettempdir()) / f'regaro-final-{label}.png'))
        page.locator('#demonstracao').scroll_into_view_if_needed()
        page.screenshot(path=str(Path(gettempdir()) / f'regaro-final-{label}-demo.png'))
        page.locator('#modulos').scroll_into_view_if_needed()
        page.screenshot(path=str(Path(gettempdir()) / f'regaro-final-{label}-modules.png'))
    page.emulate_media(reduced_motion='reduce', color_scheme='dark')
    page.goto(URL, wait_until='networkidle')
    page.locator('[data-scenario=banco]').click()
    assert page.locator('#demo-answer').evaluate('(e)=>e.getAnimations().length') == 0
    page.locator('summary').first.click()
    assert page.locator('details').first.get_attribute('open') is not None
    page.locator('.header .button').click()
    assert '/proposta/' in page.url
    print('Lead form reachable:', page.url)
    print('Console errors:', errors)
    assert not errors
    static_page = browser.new_page(java_script_enabled=False)
    static_page.goto(URL)
    assert static_page.locator('h1').is_visible()
    assert static_page.locator('.module-lines>div').count() == 4
    assert static_page.locator('noscript').is_visible()
    browser.close()
print('PASS: uncluttered hero, scenarios, evidence, focus return, 4 viewports, reduced motion, FAQ, lead navigation.')
