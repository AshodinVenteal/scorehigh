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
        assert page.locator('html').get_attribute('data-score-font') == 'plain'
        page.evaluate("localStorage.removeItem('scorehigh-players')")
        page.reload(wait_until='networkidle')
        page.locator('[data-claim-player]').first.click()
        assert page.locator('.ranking-entry.is-me').count() == 1
        page.locator('[data-follow-player]').nth(1).click()
        assert page.locator('.ranking-entry.is-followed').count() == 1
        page.locator('[data-following-filter]').click()
        assert page.locator('[data-player]:visible').count() == 2
        page.locator('[data-following-filter]').click()
        page.reload(wait_until='networkidle')
        assert page.locator('.ranking-entry.is-me').count() == 1
        assert page.locator('.ranking-entry.is-followed').count() == 1
        page.locator('[data-claim-player]').nth(2).click()
        assert page.locator('.ranking-entry.is-me').count() == 1
        assert page.locator('.ranking-entry.is-me').get_attribute('data-player') == entries.nth(2).get_attribute('data-player')
        page.locator('[data-claim-player]').first.click()
        assert page.locator('.ranking-entry.is-me').get_attribute('data-player') == name
        assert 'Snapshot:' in page.locator('[data-refresh-status]').inner_text()
        assert 'checks every 60s.' in page.locator('[data-refresh-status]').inner_text()
        choose_appearance(page, '[data-score-font-select]', 'plain')
        assert page.locator('html').get_attribute('data-score-font') == 'plain'
        choose_appearance(page, '[data-score-font-select]', 'segmented')
        page.evaluate('document.fonts.ready')
        assert page.evaluate("document.fonts.check('700 22px \"ScoreHigh Digits\"', '0123456789')")
        logo_font = page.locator('.logo-title').evaluate('(el) => getComputedStyle(el).fontFamily')
        for font_choice in ['matrix', 'alarm', 'lcd', 'highway', 'terminal', 'plain', 'segmented']:
            choose_appearance(page, '[data-score-font-select]', font_choice)
            page.evaluate('document.fonts.ready')
            assert page.locator('.logo-title').evaluate('(el) => getComputedStyle(el).fontFamily') == logo_font
            for width in [320, 390, 1280]:
                page.set_viewport_size({'width': width, 'height': 844})
                check_width(page)
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(OUTPUT / f'score-font-{font_choice}.png'), full_page=True)
        choose_appearance(page, '[data-score-font-select]', 'lcd')
        page.reload(wait_until='networkidle')
        assert page.locator('html').get_attribute('data-score-font') == 'lcd'
        choose_appearance(page, '[data-score-font-select]', 'segmented')
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
        assert page.locator('.ranking-entry.is-me').count() == 1
        assert page.locator('.ranking-entry.is-followed').count() == 1
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
        assert page.locator('.player-tracking.is-me').is_visible()
        page.locator('[data-claim-player]').click()
        assert not page.locator('.player-tracking.is-me').count()
        page.locator('[data-claim-player]').click()
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
        page.wait_for_load_state('networkidle')
        assert '/how-it-works/281672' in page.url
        assert page.locator('.tabs [aria-current="page"]').inner_text() == 'How it works'
        assert page.locator('.instructions').is_visible()
        for width in [320, 390, 1280]:
            page.set_viewport_size({'width': width, 'height': 844})
            check_width(page)
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(OUTPUT / 'how-it-works-mobile.png'), full_page=True)
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
        assert page.locator('.tabs .matchplay-tab').is_visible()
        page.goto(f'{BASE}/', wait_until='networkidle')
        icons = page.locator('.tournament-icon').all_text_contents()
        assert icons and all(icon.strip() != '#' for icon in icons)
        assert page.locator('.tournament-item .matchplay-button').first.is_visible()
        listing = page.locator('.tournament-item').first
        title_box = listing.locator('.tournament-link').bounding_box()
        link_box = listing.locator('.matchplay-button').bounding_box()
        assert link_box['x'] >= title_box['x'] + title_box['width']
        page.screenshot(path=str(OUTPUT / 'desk-mobile.png'), full_page=True)
        page.reload(wait_until='networkidle')
        assert page.locator('.tournament-icon').all_text_contents() == icons
        check_width(page)
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
