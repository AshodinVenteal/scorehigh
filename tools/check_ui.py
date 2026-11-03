"""Browser smoke checks. Run against a locally running ScoreHigh server.

uv run --with playwright python tools/check_ui.py
Uses an existing Playwright Chromium installation when available.
"""
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("SCOREHIGH_PREVIEW_URL", "http://127.0.0.1:8765")
OUTPUT = Path(__file__).resolve().parents[1] / ".preview"


def check_width(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow"
    for selector in [".score-info > strong", ".adjusted-score", ".history-total"]:
        for element in page.locator(selector).all():
            if element.is_visible():
                box = element.bounding_box()
                assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"], selector


def choose_appearance(page, selector, value):
    settings = page.locator('.display-settings')
    if settings.get_attribute('open') is None:
        settings.locator('summary').click()
    page.locator(selector).select_option(value)
    page.wait_for_load_state('networkidle')
    settings.locator('summary').click()


def main():
    OUTPUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        cached = list((Path(os.environ["LOCALAPPDATA"]) / "ms-playwright").glob("chromium-*/chrome-win*/chrome.exe"))
        browser = p.chromium.launch(executable_path=str(cached[-1]) if cached else None)
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(f"{BASE}/ranking/281672", wait_until="networkidle")
        assert response.status == 200
        page.evaluate("localStorage.setItem('scorehigh-theme', 'light'); localStorage.setItem('scorehigh-style', 'windows')")
        page.reload(wait_until="networkidle")
        entries = page.locator('[data-player]')
        assert entries.count() > 0
        name = entries.first.get_attribute('data-player')
        score = page.locator('.score-info > strong').first.inner_text()
        for width in [320, 375, 390, 768, 1280]:
            page.set_viewport_size({"width": width, "height": 900 if width > 600 else 844})
            check_width(page)
            page.screenshot(path=str(OUTPUT / f"standings-{width}.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        search = page.locator('[data-player-search]')
        search.fill(name)
        assert page.locator('[data-player]:visible').count() >= 1
        assert page.locator('[data-player]:visible').first.locator('.rank').inner_text() == '1'
        search.fill('no such player 92834')
        assert page.locator('[data-search-empty]').is_visible()
        page.locator('[data-clear-search]').click()
        assert page.locator('[data-player]:visible').count() == entries.count()
        page.locator('[data-expand]').click()
        assert page.locator('.card-details[open]').count() == entries.count()
        check_width(page)
        page.screenshot(path=str(OUTPUT / 'standings-expanded-mobile.png'), full_page=True)
        search.fill(name)
        page.locator('[data-refresh]').click()
        page.wait_for_function("!document.querySelector('[data-refresh]').disabled")
        assert search.input_value() == name
        assert page.locator('.card-details').first.get_attribute('open') is not None
        assert page.locator('.score-info > strong').first.inner_text() == score
        ranking_url = re.compile(r'/ranking/281672/?(?:\?.*)?$')
        page.route(ranking_url, lambda route: route.fulfill(status=503, body='Unavailable'))
        page.locator('[data-refresh]').click()
        page.wait_for_function("document.querySelector('[data-refresh-status]').dataset.error === 'true'")
        assert page.locator('.score-info > strong').first.inner_text() == score
        page.screenshot(path=str(OUTPUT / 'update-failure-mobile.png'), full_page=True)
        page.unroute(ranking_url)
        page.locator('[data-refresh]').click()
        page.wait_for_function("!document.querySelector('[data-refresh]').disabled")
        assert page.locator('[data-refresh-status]').get_attribute('data-error') is None
        page.locator('[data-auto]').click()
        assert page.locator('[data-auto]').get_attribute('aria-pressed') == 'false'
        choose_appearance(page, '[data-theme-select]', 'dark')
        assert page.locator('html').get_attribute('data-theme') == 'dark'
        page.screenshot(path=str(OUTPUT / 'standings-dark-mobile.png'), full_page=True)
        choose_appearance(page, '[data-theme-select]', 'system')
        page.emulate_media(color_scheme='dark')
        page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
        page.emulate_media(color_scheme='light')
        page.wait_for_function("document.documentElement.dataset.theme === 'light'")
        choose_appearance(page, '[data-theme-select]', 'light')
        page.locator('[data-player]:visible').first.locator('.player-info > a').click()
        page.wait_for_load_state('networkidle')
        assert page.locator('.player-stats').is_visible()
        for width in [320, 390, 1280]:
            page.set_viewport_size({"width": width, "height": 844})
            check_width(page)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(OUTPUT / 'player-mobile.png'), full_page=True)
        page.get_by_role('link', name='Machines', exact=True).click()
        page.wait_for_load_state('networkidle')
        assert page.locator('.machine-catalog-row').count() > 0
        check_width(page)
        page.screenshot(path=str(OUTPUT / 'machines-mobile.png'), full_page=True)
        page.get_by_role('link', name='How it works', exact=True).click()
        assert page.locator('#format').get_attribute('open') is not None
        choose_appearance(page, '[data-style-select]', 'portal')
        assert page.locator('html').get_attribute('data-style') == 'portal'
        page.goto(f'{BASE}/ranking/281672', wait_until='networkidle')
        assert page.locator('[data-style-select]').input_value() == 'portal'
        assert page.locator('html').get_attribute('data-style') == 'portal'
        for width in [320, 375, 390, 768, 1280]:
            page.set_viewport_size({'width': width, 'height': 900 if width > 600 else 844})
            check_width(page)
            page.screenshot(path=str(OUTPUT / f'portal-{width}.png'), full_page=True)
        assert page.locator('.portal-directory').is_visible()
        page.set_viewport_size({'width': 390, 'height': 844})
        choose_appearance(page, '[data-theme-select]', 'dark')
        check_width(page)
        page.screenshot(path=str(OUTPUT / 'portal-dark-mobile.png'), full_page=True)
        page.locator('[data-player-search]').fill(name)
        assert page.locator('[data-player]:visible').count() >= 1
        page.locator('[data-expand]').click()
        check_width(page)
        choose_appearance(page, '[data-style-select]', 'windows')
        assert page.locator('[data-player-search]').input_value() == name
        assert page.locator('.card-details[open]').count() > 0
        assert not page.locator('.portal-directory').is_visible()
        assert not errors, errors
        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 320, "height": 844})
        plain = no_js.new_page()
        assert plain.goto(f'{BASE}/ranking/281672').status == 200
        assert not plain.locator('[data-search-toolbar]').is_visible()
        plain.locator('.card-details > summary').first.click()
        assert plain.locator('.game-breakdown').first.is_visible()
        check_width(plain)
        browser.close()
        print('PASS: Windows/Portal styles and persistence; mobile/desktop layouts; search; breakdowns; refresh state; failed updates; light/dark/system themes; player history; machines; rules; no-JS fallback.')
        print(f'Screenshots: {OUTPUT}')


if __name__ == '__main__':
    main()
