// Выгрузка времён событий 3D-сцены (вспышки фейерверков) для звука: node export_events.js out.json
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const ROOT = __dirname;
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.route('http://local/**', r => {
    const u = new URL(r.request().url()).pathname;
    const f = u === '/' || u === '/index.html' ? path.join(ROOT, 'index.html') : u.startsWith('/three/') ? path.join(ROOT, 'node_modules/three/build', u.slice(7)) : path.join(ROOT, u.slice(1));
    r.fulfill({ status: 200, contentType: f.endsWith('.js') ? 'text/javascript' : 'text/html', body: fs.readFileSync(f) });
  });
  await p.goto('http://local/index.html'); await p.waitForFunction(() => window.READY === true);
  const ev = await p.evaluate(async () => { const L = (await import('/loc_london.js')).default; return { bursts: L.bursts, strikes: [41.9, 45.3, 47.6] }; });
  fs.writeFileSync(process.argv[2], JSON.stringify(ev)); console.log(ev.bursts.length, 'bursts');
  await b.close();
})();
