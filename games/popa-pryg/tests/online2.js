// Online extras on a test Worker: reconnect after a drop, reactions, watching the friend, rematch.
const { chromium } = require('playwright');
const URL = (process.argv[2] || 'https://popa-pryg-test.giftstelegram01.workers.dev') + '/';
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const errs = [];
  const mk = async tag => { const c = await b.newContext({ viewport: { width: 390, height: 844 } }); const p = await c.newPage(); p.on('pageerror', e => errs.push(tag + ': ' + e.message)); await p.goto(URL + '?v=' + Date.now()); await p.waitForTimeout(1500); return p; };
  const A = await mk('A'), B = await mk('B');
  for (const p of [A, B]) { await p.click('#mPlay'); await p.click('#onlineBtn'); await p.waitForTimeout(700); }
  await A.waitForTimeout(2500);
  for (const p of [A, B]) await p.evaluate(() => { window.__popa.auto(true); window.__skip = 8; });
  await A.waitForTimeout(6000);
  const info = p => p.evaluate(() => window.__popa.info());
  console.log('playing:', (await info(A)).state, (await info(B)).state, '| reactions button:', await A.isVisible('#emoBtn'));
  // connection drop on A
  await A.evaluate(() => window.__popa.dropNet()); await A.waitForTimeout(6000);
  const a1 = await info(A), b1 = await info(B);
  console.log('after drop: A sees friend gone?', a1.mate.gone, '| B sees A gone?', b1.mate.gone);
  console.log('A messages:', (await A.evaluate(() => window.__popa.msgs())).filter(t => /связ|Связ/.test(t)).join(' / '));
  console.log('B messages:', (await B.evaluate(() => window.__popa.msgs())).filter(t => /связ|снова/.test(t)).join(' / '));
  // reaction from A appears for B (sprite count)
  await A.click('#emoBtn'); await A.click('#emoRow button:nth-child(4)'); await A.waitForTimeout(800);
  // A falls, watches B; then B falls and both ask for a rematch
  await A.evaluate(() => window.__popa.kill()); await A.waitForTimeout(3000);
  console.log('A over screen, watch button:', await A.isVisible('#watchBtn'), '| rematch hidden while B alive:', !(await A.isVisible('#rematchBtn')));
  await A.click('#watchBtn'); await A.waitForTimeout(1500);
  console.log('A watching (over screen hidden):', !(await A.isVisible('#overScreen')));
  await B.evaluate(() => window.__popa.kill()); await B.waitForTimeout(3500);
  console.log('A back on over screen with rematch:', await A.isVisible('#rematchBtn'), '| B rematch:', await B.isVisible('#rematchBtn'));
  await A.click('#rematchBtn'); await A.waitForTimeout(800);
  console.log('B button after A asked:', await B.textContent('#rematchBtn'));
  await B.click('#rematchBtn'); await A.waitForTimeout(2500);
  console.log('rematch started:', (await info(A)).state, (await info(B)).state);
  console.log(errs.join('\n') || 'no errors'); await b.close();
})();
