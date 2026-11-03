// Рендер 3D-прохода в PNG: node render_scene.js <outDir> <from> <to> [--frames a,b,c]
// Кадры — функция времени i/60. Маски берутся из ../build/masks (готовит prep_masks.py).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const MASKS = path.join(ROOT, '..', 'build', 'masks');
const THREE_DIR = path.join(ROOT, 'node_modules', 'three', 'build');
const FPS = 60;

function fileFor(p) {
  if (p === '/' || p === '/index.html') return path.join(ROOT, 'index.html');
  if (p.startsWith('/three/')) return path.join(THREE_DIR, p.slice(7));
  if (p.startsWith('/masks/')) return path.join(MASKS, p.slice(7));
  return path.join(ROOT, p.slice(1));
}

(async () => {
  const args = process.argv.slice(2);
  const outDir = args[0];
  let list;
  const fi = args.indexOf('--frames');
  if (fi >= 0) list = args[fi + 1].split(',').map(Number);
  else { list = []; for (let i = +args[1]; i < +args[2]; i++) list.push(i); }
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.log('[error]', e.message));
  await page.route('http://local/**', route => {
    const file = fileFor(new URL(route.request().url()).pathname);
    if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: 'missing ' + file });
    const type = file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/html';
    route.fulfill({ status: 200, contentType: type, body: fs.readFileSync(file) });
  });
  await page.goto('http://local/index.html');
  await page.waitForFunction(() => window.READY === true, null, { timeout: 180000 });
  const t0 = Date.now();
  for (let n = 0; n < list.length; n++) {
    const i = list[n];
    const data = await page.evaluate(t => window.renderAt(t), i / FPS);
    fs.writeFileSync(path.join(outDir, `f${String(i).padStart(5, '0')}.png`), Buffer.from(data.split(',')[1], 'base64'));
    if (n % 20 === 0 || n === list.length - 1) console.log(`frame ${i} (${n + 1}/${list.length}) ${((Date.now() - t0) / (n + 1) / 1000).toFixed(2)} s/frame`);
  }
  await browser.close();
})();
