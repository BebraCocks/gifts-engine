// Screens of the economy: menu row, upgrades, profile, game over. Usage: BOT_TOKEN=... node econ-ui.js https://popa-pryg-test....workers.dev
const crypto = require('crypto'); const fs = require('fs');
const { chromium } = require('playwright');
const BASE = process.argv[2], TOKEN = process.env.BOT_TOKEN;
fs.mkdirSync(__dirname + '/shots', { recursive: true });
const sign = (id, first) => {
  const p = new URLSearchParams({ auth_date: String(Math.floor(Date.now() / 1000)), query_id: 'q' + id, user: JSON.stringify({ id, first_name: first }) });
  const check = [...p.entries()].sort(([a], [b]) => a < b ? -1 : 1).map(([k, v]) => `${k}=${v}`).join('\n');
  p.set('hash', crypto.createHmac('sha256', crypto.createHmac('sha256', 'WebAppData').update(TOKEN).digest()).update(check).digest('hex'));
  return p.toString();
};
const api = (init, op, body) => fetch(`${BASE}/api/${op}`, { method: 'POST', headers: { 'X-Tg-Init': init, 'content-type': 'application/json' }, body: JSON.stringify(body || {}) }).then(r => r.json());
(async () => {
  const init = sign(820000000 + Math.floor(Math.random() * 1e6), 'Эко');
  await api(init, 'name', { name: 'Попкоин-тест' });
  for (let k = 0; k < 3; k++) await api(init, 'score', { mode: 'story', score: 900, secs: 120, bosses: 3, coins: 40 });
  await api(init, 'upgrade', { id: 'piggy' }); await api(init, 'upgrade', { id: 'magnet' }); await api(init, 'upgrade', { id: 'magnet' });
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.route('**/telegram-web-app.js', r => r.fulfill({ contentType: 'text/javascript', body: `window.Telegram = { WebApp: { initData: ${JSON.stringify(init)}, initDataUnsafe: { user: { first_name: 'Эко' } }, ready(){}, expand(){}, isVersionAtLeast(){ return true; }, disableVerticalSwipes(){}, requestFullscreen(){}, lockOrientation(){}, setHeaderColor(){}, setBackgroundColor(){} } };` }));
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(BASE + '/?v=' + Date.now()); await p.waitForTimeout(2500);
  await p.evaluate(() => { window.__skip = 4; });
  const shot = n => p.screenshot({ path: `${__dirname}/shots/econ-${n}.png` });
  await shot('1-menu');
  await p.click('#mShop'); await p.waitForTimeout(1500); await shot('2-upgrades');
  await p.click('[data-upg="shield"]'); await p.waitForTimeout(1500); await shot('3-bought');
  await p.click('#panelClose'); await p.click('#mProfile'); await p.waitForTimeout(1500); await shot('4-profile');
  await p.click('#panelClose'); await p.click('#mPlay'); await p.click('#endlessBtn'); await p.waitForTimeout(1500); await shot('5-run');
  await p.evaluate(() => window.__popa.auto(true)); await p.waitForTimeout(8000);
  await p.evaluate(() => window.__popa.auto(false)); await p.evaluate(() => window.__popa.kill()); await p.waitForTimeout(5000); await shot('6-over');
  console.log('errors', errs); await b.close();
})();
