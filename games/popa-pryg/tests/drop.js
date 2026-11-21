const { chromium } = require('playwright');
const URL = 'https://popa-pryg-test.giftstelegram01.workers.dev/?v=' + Date.now();
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const mk = async () => { const c = await b.newContext({ viewport: { width: 390, height: 844 } }); const p = await c.newPage(); p.on('pageerror', e => console.log('ERR', e.message)); await p.goto(URL); await p.waitForTimeout(1500); return p; };
  const A = await mk(), B = await mk();
  for (const p of [A, B]) { await p.click('#mPlay'); await p.click('#onlineBtn'); await p.waitForTimeout(700); }
  await A.waitForTimeout(3000);
  const show = async (tag) => { const i = await A.evaluate(() => window.__popa.info()); console.log(tag, JSON.stringify({ state: i.state, tok: i.tok, rt: i.rt, ws: i.ws, leaving: i.leaving, mateGone: i.mate && i.mate.gone })); };
  await show('before drop');
  await A.evaluate(() => window.__popa.dropNet());
  for (let k = 0; k < 8; k++) { await A.waitForTimeout(1000); await show('t+' + (k + 1) + 's'); }
  console.log('A pops:', (await A.evaluate(() => window.__popa.msgs())).join(' / '));
  console.log('B pops:', (await B.evaluate(() => window.__popa.msgs())).join(' / '));
  await b.close();
})();
