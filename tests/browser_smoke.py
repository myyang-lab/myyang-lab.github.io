"""Optional browser regression checks: pip install playwright==1.62.0; playwright install chromium."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['index', 'research', 'people', 'publications', 'news', 'gallery', 'contact', 'moon-young-yang']
WIDTHS = [1440, 1050, 980, 768, 731, 730, 700, 651, 650, 390, 320]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT)
    parser.add_argument('--screenshots', type=Path)
    parser.add_argument('--metrics', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(args.site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors, metrics = [], {}
    try:
        with sync_playwright() as p:
            executable = shutil.which('chromium') or shutil.which('chromium-browser')
            browser = p.chromium.launch(**({'executable_path': executable} if executable else {}))
            page = browser.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}') if response.status >= 400 else None)
            for name in PAGES:
                for width in WIDTHS:
                    page.set_viewport_size({'width': width, 'height': 900})
                    response = page.goto(f'http://127.0.0.1:{server.server_port}/{name}.html')
                    assert response.status == 200, (name, width)
                    page.evaluate('document.fonts.ready')
                    # Force lazy images to load before inspecting their intrinsic sizes.
                    page.locator('img').evaluate_all("images => images.forEach(image => image.loading = 'eager')")
                    page.wait_for_function('Array.from(document.images).every(image => image.complete)')
                    assert page.locator('h1').count() == 1, name
                    assert page.locator('.nav-links a[aria-current="page"]').count() == 1, name
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Horizontal overflow: {name} @ {width}'
                    assert page.locator('img').evaluate_all('images => images.every(image => image.naturalWidth > 0)'), name
                    if name == 'research':
                        geometry = page.locator('.research-section').evaluate_all("sections => sections.map(s => Object.fromEntries(['.wrap','.research-heading','.research-description','.research-copy','.research-art'].map(k => [k, s.querySelector(k).getBoundingClientRect().toJSON()])))")
                        for index, area in enumerate(geometry):
                            assert abs(area['.research-heading']['x'] - area['.wrap']['x']) < 1
                            assert abs(area['.research-description']['width'] - area['.wrap']['width']) < 1
                            assert area['.research-art']['y'] >= area['.research-description']['bottom']
                            if width > 650:
                                assert (area['.research-copy']['x'] < area['.research-art']['x']) == (index % 2 == 0)
                                assert abs(area['.research-art']['height'] - area['.research-copy']['height']) < 1
                    button, menu = page.locator('.menu-toggle'), page.locator('#primary-navigation')
                    if width <= 730:
                        assert button.is_visible() and not menu.is_visible(), (name, width)
                        button.click()
                        assert menu.is_visible() and button.get_attribute('aria-expanded') == 'true', (name, width)
                        rect, header = menu.bounding_box(), page.locator('.nav-inner').bounding_box()
                        assert rect['y'] >= header['y'] + header['height'] - 1, (name, width, 'overlapping menu')
                        page.keyboard.press('Escape')
                        assert not menu.is_visible() and button.get_attribute('aria-expanded') == 'false'
                        assert button.evaluate('el => el === document.activeElement')
                        # Native button activation works with keyboard as well as pointer.
                        page.keyboard.press('Enter')
                        assert menu.is_visible()
                        page.mouse.click(width - 2, 850)
                        assert not menu.is_visible()
                        # Returning to desktop and back should not leave the mobile menu open.
                        button.click()
                        page.set_viewport_size({'width': 1000, 'height': 900})
                        expect(menu).to_be_visible()
                        expect(button).not_to_be_visible()
                        expect(button).to_have_attribute('aria-expanded', 'false')
                        page.set_viewport_size({'width': width, 'height': 900})
                        expect(menu).not_to_be_visible()
                    else:
                        assert menu.is_visible() and not button.is_visible(), (name, width)
                    page.evaluate("() => { document.activeElement.blur(); window.scrollTo({top: 0, behavior: 'instant'}); }")
                    metrics[f'{name}-{width}'] = page.evaluate('''() => {const out={}; for(const s of ['.nav','.nav-inner','.logo','.brand-primary','.brand-secondary','.nav-links','h1','.hero','.direction','.pagehead','.page-hero','.page-header','.person-card','.pub','.gallery-card','.footer','.footer-inner']){const el=document.querySelector(s);if(!el)continue; const c=getComputedStyle(el);out[s]={rect:JSON.parse(JSON.stringify(el.getBoundingClientRect())),css:Object.fromEntries(['fontFamily','fontSize','lineHeight','color','backgroundColor','padding','margin','display','flexDirection','gap','width','maxWidth','borderRadius'].map(k=>[k,c[k]]))};}return out;}''')
                    if args.screenshots and width in [1440, 390]:
                        page.screenshot(path=str(args.screenshots / f'{name}-{width}.png'), full_page=True)
            # Enlargements stay in the same page, close by pointer/keyboard, and restore focus.
            for name in ['gallery', 'research']:
                for width in [1440, 390]:
                    page.set_viewport_size({'width': width, 'height': 900})
                    page.goto(f'http://127.0.0.1:{server.server_port}/{name}.html')
                    original_url = page.url
                    triggers = page.locator('[data-image-viewer]')
                    assert triggers.count() == (4 if name == 'research' else len(json.loads((ROOT / 'data/gallery.json').read_text())))
                    for index in range(triggers.count()):
                        trigger = triggers.nth(index)
                        trigger.scroll_into_view_if_needed()
                        trigger.focus()
                        page.keyboard.press('Enter')
                        viewer = page.locator('dialog.image-viewer')
                        expect(viewer).to_be_visible()
                        image = viewer.locator('img')
                        image.evaluate('i => i.decode()')
                        assert image.evaluate('i => i.naturalWidth > 0')
                        assert image.get_attribute('alt') == trigger.locator('img').get_attribute('alt')
                        assert page.url == original_url and len(page.context.pages) == 1
                        assert page.evaluate("document.documentElement.style.overflow === 'hidden'")
                        box = image.bounding_box()
                        assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
                        assert box['y'] >= 0 and box['y'] + box['height'] <= 901
                        if index % 4 == 0:
                            image.click()
                        elif index % 4 == 1:
                            page.keyboard.press('Escape')
                        elif index % 4 == 2:
                            viewer.get_by_role('button', name='Close enlarged image').click()
                        else:
                            page.mouse.click(3, 100)
                        expect(viewer).to_have_count(0)
                        expect(trigger).to_be_focused()
                        assert page.evaluate("document.documentElement.style.overflow !== 'hidden'")
                        assert page.url == original_url and len(page.context.pages) == 1
            page.goto(f'http://127.0.0.1:{server.server_port}/publications.html')
            assert page.locator('article.pub').count() == len(json.loads((ROOT / 'data/publications.json').read_text()))
            assert '2073–2093' in page.locator('#paper-60').inner_text()
            assert 'Mingyang Liu' in page.locator('#paper-62').inner_text()
            assert 'Accepted' in page.locator('#paper-63 .pub-meta').inner_text()
            assert '2026' not in page.locator('#paper-63 .pub-meta').inner_text()
            page.goto(f'http://127.0.0.1:{server.server_port}/gallery.html')
            assert page.locator('figure.gallery-card').count() == len(json.loads((ROOT / 'data/gallery.json').read_text()))
            page.goto(f'http://127.0.0.1:{server.server_port}/join.html')
            page.wait_for_url('**/contact.html')
            assert not errors, errors
            browser.close()
        if args.metrics:
            args.metrics.write_text(json.dumps(metrics))
        print(f'Browser checks passed: {len(PAGES)} pages × {len(WIDTHS)} widths; menu pointer/keyboard/resize, images, publications and redirect.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
