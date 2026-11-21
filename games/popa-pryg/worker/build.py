"""Builds worker/public/index.html from game/popa-pryg.html: a full HTML page with the Telegram SDK and full-screen setup."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
src = (ROOT.parent / 'game' / 'popa-pryg.html').read_text(encoding='utf-8')
head = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#3aa8ff">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script>
  // Inside Telegram: full screen, portrait, and the swipe-down gesture never closes the game while you steer.
  (() => {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.initData) return;
    const v = q => tg.isVersionAtLeast && tg.isVersionAtLeast(q);
    try { tg.ready(); tg.expand(); } catch (e) {}
    try { if (v('7.7')) tg.disableVerticalSwipes(); } catch (e) {}
    try { if (v('8.0')) { tg.requestFullscreen(); tg.lockOrientation(); } } catch (e) {}
    try { tg.setHeaderColor('#1478f0'); tg.setBackgroundColor('#8fd6ff'); } catch (e) {}
  })();
</script>
"""
# three.js goes inside the page, so the game never depends on an outside CDN (MIT licence, see vendor/three.min.js header)
CDN = '<script src="https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js"></script>'
three = (ROOT / 'vendor' / 'three.min.js').read_text(encoding='utf-8')
assert CDN in src, 'three.js script tag not found in the game file'
src = src.replace(CDN, '<script>' + three.replace('</script', '<\\/script') + '</script>')
i = src.index('<canvas id="game"')
page = head + src[:i] + "</head>\n<body>\n" + src[i:].rstrip() + "\n</body>\n</html>\n"
out = ROOT / 'public' / 'index.html'
out.write_text(page, encoding='utf-8')
print('built', out, len(page))
