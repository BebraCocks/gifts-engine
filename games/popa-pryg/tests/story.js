// Story mode with the autopilot on #test: should reach the ending.
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 390, height: 844 } }); const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.resolve(__dirname, '../game/popa-pryg.html') + '#test'); await p.waitForTimeout(900);
  await p.evaluate(() => { window.__skip = 10; });
  await p.click('#mPlay'); await p.click('#playBtn'); await p.evaluate(() => window.__popa.auto(true));
  const seen = []; let lastBoss = null; const t0 = Date.now();
  while (Date.now() - t0 < 900000) {
    const i = await p.evaluate(() => window.__popa.info());
    if (i.state === 'boss' && i.boss !== lastBoss) { lastBoss = i.boss; seen.push(i.boss); }
    if (i.state !== 'boss') lastBoss = null;
    if (i.state === 'over' || i.state === 'finale' || false) { console.log('state', i.state, 'row', i.curIdx, 'bosses won', i.bossesWon, 'score', i.score); break; }
    await p.waitForTimeout(400);
  }
  console.log('boss order:', seen.map(n => n + 1).join(' '));
  console.log(errs.join('\n') || 'no errors'); await b.close();
})();
