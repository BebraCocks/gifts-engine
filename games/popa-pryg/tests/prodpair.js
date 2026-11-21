// Production smoke test: two random-online players get paired (no accounts are created).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const errs = [];
  const mk = async () => { const c = await b.newContext({ viewport: { width: 390, height: 844 } }); const p = await c.newPage(); p.on('pageerror', e => errs.push(e.message)); await p.goto('https://popa-pryg.giftstelegram01.workers.dev/?v=' + Date.now()); await p.waitForTimeout(1500); return p; };
  const A = await mk(), B = await mk();
  for (const p of [A, B]) { await p.click('#mPlay'); await p.click('#onlineBtn'); await p.waitForTimeout(800); }
  await A.waitForTimeout(4000);
  const a = await A.evaluate(() => window.__popa.info()), bb = await B.evaluate(() => window.__popa.info());
  console.log('A', a.state, 'host', a.host, '| B', bb.state, 'host', bb.host, '| mic hidden in random:', !(await A.isVisible('#micBtn')));
  console.log(errs.join('\n') || 'no errors'); await b.close();
})();
