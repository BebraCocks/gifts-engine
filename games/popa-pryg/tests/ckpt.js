// Story checkpoint (#test: boss every 6 rows) and the daily challenge being the same track every time.
const { chromium } = require('playwright'); const path = require('path');
const FILE = 'file://' + path.resolve(__dirname, '../game/popa-pryg.html');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const errs = [];
  const p = await b.newPage({ viewport: { width: 390, height: 844 } }); p.on('pageerror', e => errs.push(e.message));
  await p.goto(FILE + '#test'); await p.waitForTimeout(900);
  await p.click('#mPlay'); await p.click('#playBtn'); await p.evaluate(() => { window.__popa.auto(true); window.__skip = 8; });
  for (let k = 0; k < 600; k++) { const i = await p.evaluate(() => window.__popa.info()); if (i.curIdx >= 12 && i.state === 'boss') break; await p.waitForTimeout(250); }
  const before = await p.evaluate(() => window.__popa.info());
  console.log('reached boss 2 at row', before.curIdx, 'score', before.score, '| saved:', await p.evaluate(() => localStorage.getItem('popa-ckpt')));
  await p.keyboard.press('Escape'); await p.click('#pauseMenu'); await p.waitForTimeout(400);
  await p.click('#mPlay'); await p.click('#playBtn'); await p.waitForTimeout(300);
  console.log('story dialog:', await p.textContent('#modalTitle'), '|', await p.textContent('#modalText'), '|', await p.textContent('#modalBtns'));
  await p.click('#modalBtns .btn:not(.ghost)'); await p.waitForTimeout(800);
  const after = await p.evaluate(() => window.__popa.info());
  console.log('continued at row', after.curIdx, 'score', after.score, 'bosses won', after.bossesWon);
  // daily: same first rows twice
  const rows = async () => { await p.evaluate(() => window.__popa.auto(false)); return p.evaluate(() => [3, 6, 9, 12].map(i => window.__popa.rowInfo(i).x.toFixed(2)).join(',')); };
  await p.keyboard.press('Escape'); await p.click('#pauseMenu'); await p.waitForTimeout(300);
  await p.click('#mPlay'); await p.click('#dailyBtn'); await p.waitForTimeout(500); const d1 = await rows();
  await p.keyboard.press('Escape'); await p.click('#pauseMenu'); await p.waitForTimeout(300);
  await p.click('#mPlay'); await p.click('#endlessBtn'); await p.waitForTimeout(500); const e1 = await rows();
  await p.keyboard.press('Escape'); await p.click('#pauseMenu'); await p.waitForTimeout(300);
  await p.click('#mPlay'); await p.click('#dailyBtn'); await p.waitForTimeout(500); const d2 = await rows();
  console.log('daily twice the same:', d1 === d2, '| endless differs:', d1 !== e1);
  console.log(errs.join('\n') || 'no errors'); await b.close();
})();
