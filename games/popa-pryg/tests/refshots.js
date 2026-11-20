// Reference screenshots of the current interface for the artist.
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.resolve(__dirname, '../game/popa-pryg.html') + '#test'); await p.waitForTimeout(1500);
  const s = n => p.screenshot({ path: __dirname + '/shots/ref-' + n + '.png' });
  await s('1-menu');
  await p.click('#mPlay'); await p.waitForTimeout(200); await s('2-play'); await p.click('#playBack');
  await p.click('#mSettings'); await p.waitForTimeout(200); await s('3-settings'); await p.click('#panelClose');
  await p.click('#mPlay'); await p.click('#endlessBtn'); await p.waitForTimeout(2500); await s('4-game');
  await p.keyboard.press('Escape'); await p.waitForTimeout(300); await s('5-pause');
  await p.click('#resumeBtn'); await p.evaluate(() => window.__popa.kill()); await p.waitForTimeout(2500); await s('6-over');
  await b.close();
})();
