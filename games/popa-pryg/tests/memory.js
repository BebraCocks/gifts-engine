// Solo autopilot run on #specials: prints GPU geometry/texture counts as the run goes, to catch leaks.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + path.resolve(__dirname, '../game/popa-pryg.html') + (process.argv[2] || '#specials'));
  await p.waitForTimeout(900);
  await p.evaluate(() => { window.__skip = 10; });
  await p.click('#playBtn'); await p.evaluate(() => window.__popa.auto(true));
  const t0 = Date.now(); let lastIdx = -1;
  while (Date.now() - t0 < (+process.argv[3] || 420000)) {
    const i = await p.evaluate(() => window.__popa.info());
    if (i.curIdx >= lastIdx + 10 || i.state === 'over') { lastIdx = i.curIdx; console.log(`row ${i.curIdx} state ${i.state} rows-in-scene ${i.rows} geometries ${i.geo} textures ${i.tex}`); }
    if (i.state === 'over' || i.state === 'finale') break;
    await p.waitForTimeout(700);
  }
  await b.close();
})();
