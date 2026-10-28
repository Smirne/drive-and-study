"""Serve public/ over HTTP and check the home page, lessons player and cross-links."""
import functools, http.server, re, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory='public')
handler.log_message = lambda *a: None


class CleanUrls(http.server.SimpleHTTPRequestHandler):
    # mimic Vercel cleanUrls: /drill -> drill.html
    def translate_path(self, path):
        p = super().translate_path(path)
        return p + '.html' if not Path(p).exists() and Path(p + '.html').exists() else p
    def log_message(self, *a): pass


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(CleanUrls, directory='public'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{srv.server_port}'

# every lesson listed in the player has an audio file
src = Path('public/lessons.html').read_text()
n = len(re.findall(r'\{ t: "', src))
files = sorted(Path('public/audio/lessons').glob('ep*.mp3'))
assert n == len(files), (n, len(files))
print(f'lessons listed: {n}, audio files: {len(files)}')

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    bad = []; pg.on('response', lambda r: r.status >= 400 and bad.append((r.status, r.url)))
    pg.goto(base + '/'); print('home:', pg.title())
    pg.click('a[href="/lessons"]'); pg.wait_for_selector('#list li')
    print('lessons:', pg.title(), '| items:', pg.locator('#list li').count(), '| now:', pg.text_content('#nowTitle'))
    pg.click('#ep-10'); pg.wait_for_timeout(500)
    print('picked ep11 ->', pg.text_content('#nowEp'), '| src:', pg.evaluate('document.getElementById("audio").src').split('/')[-1])
    pg.click('a.drill'); pg.wait_for_selector('#startAll'); print('drill:', pg.title())
    pg.click('a[href="/lessons"]'); pg.wait_for_selector('#list li'); print('back to lessons ok')
    pg.click('a.home'); pg.wait_for_selector('a.card'); print('back home ok')
    sw = pg.evaluate('document.documentElement.scrollWidth'); print('home scrollWidth at 390px:', sw)
    print('http errors:', [x for x in bad if 'fonts.g' not in x[1]], '| page errors:', errs)
    b.close()
srv.shutdown()
