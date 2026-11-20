// Navigation check: back buttons in panels, pause/resume/exit, settings, Escape as "back", first-time hints.
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 390, height: 844 } }); const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.resolve(__dirname, '../game/popa-pryg.html') + '#test'); await p.waitForTimeout(1000);
  const vis = id => p.isVisible('#' + id);
  await p.click('#mFriends'); console.log('friends open:', await vis('panel'));
  await p.click('#panelClose'); console.log('back closes panel:', !(await vis('panel')));
  await p.click('#mSettings'); await p.waitForTimeout(200); await p.screenshot({ path: __dirname + '/shots/n1-settings.png' });
  await p.keyboard.press('Escape'); console.log('Escape closes settings:', !(await vis('panel')));
  await p.click('#mPlay'); await p.keyboard.press('Escape'); console.log('Escape leaves play submenu:', await vis('menuMain'));
  await p.click('#mPlay'); await p.click('#playBtn'); await p.waitForTimeout(1500);
  console.log('pause button in run:', await vis('pauseBtn'));
  await p.click('#pauseBtn'); await p.waitForTimeout(300);
  const z1 = (await p.evaluate(() => window.__popa.info())).pz; await p.waitForTimeout(1200); const z2 = (await p.evaluate(() => window.__popa.info())).pz;
  console.log('paused screen:', await vis('pauseScreen'), '| game frozen:', z1 === z2);
  await p.screenshot({ path: __dirname + '/shots/n2-pause.png' });
  await p.click('#resumeBtn'); await p.waitForTimeout(800); const z3 = (await p.evaluate(() => window.__popa.info())).pz;
  console.log('resumed and moving:', z3 !== z2);
  await p.keyboard.press('Escape'); await p.waitForTimeout(200); console.log('Escape in run pauses:', await vis('pauseScreen'));
  await p.click('#pauseMenu'); await p.waitForTimeout(500); console.log('exit to menu:', await vis('startScreen'));
  await p.click('#mPlay'); await p.click('#playBtn'); await p.evaluate(() => { window.__popa.auto(true); window.__skip = 6; });
  for (let k = 0; k < 120; k++) { const i = await p.evaluate(() => window.__popa.info()); if (i.state === 'boss') break; await p.waitForTimeout(250); }
  await p.evaluate(() => { window.__skip = 0; }); await p.waitForTimeout(300);
  console.log('boss hint:', await vis('hintCard'), '|', await p.textContent('#hintTitle'));
  await p.screenshot({ path: __dirname + '/shots/n3-hint.png' });
  console.log(errs.join('\n') || 'no errors'); await b.close();
})();
