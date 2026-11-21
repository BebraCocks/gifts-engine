// End-to-end check of menus, profile, friends, leaderboard and friend invites, with two fake signed Telegram users.
// Usage: BOT_TOKEN=... node ui.js https://popa-pryg-test.giftstelegram01.workers.dev  (screenshots go to ./shots)
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
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const errs = [];
  const id0 = 800000000 + Math.floor(Math.random() * 1e6);
  const mk = async (tag, init, query = '') => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    await ctx.route('**/telegram-web-app.js', r => r.fulfill({ contentType: 'text/javascript', body: `window.Telegram = { WebApp: { initData: ${JSON.stringify(init)}, initDataUnsafe: { user: { first_name: '${tag}' } }, ready(){}, expand(){}, isVersionAtLeast(){ return true; }, disableVerticalSwipes(){}, requestFullscreen(){}, lockOrientation(){}, setHeaderColor(){}, setBackgroundColor(){} } };` }));
    const p = await ctx.newPage(); p.on('pageerror', e => errs.push(tag + ': ' + e.message));
    await p.goto(BASE + '/' + query); await p.waitForTimeout(2200); return p;
  };
  const initA = sign(id0 + 1, 'Аня'), initB = sign(id0 + 2, 'Боря');
  const shot = (p, n) => p.screenshot({ path: `${__dirname}/shots/${n}.png` });
  const A = await mk('Аня', initA);
  console.log('A first launch shows name dialog:', await A.isVisible('#modal'), '|', await A.textContent('#modalTitle'));
  await shot(A, '01-name');
  await A.fill('#nameField', 'Аня 🍑'); await A.click('#modalBtns .btn:not(.ghost)'); await A.waitForTimeout(1500);
  console.log('A me row:', await A.textContent('#meName'), await A.textContent('#meId'));
  await shot(A, '02-menu');
  await A.click('#mPlay'); await A.waitForTimeout(300); await shot(A, '03-play'); await A.click('#playBack');
  await A.click('#mProfile'); await A.waitForTimeout(1500); await shot(A, '04-profile');
  await A.click('#panelClose');
  const B = await mk('Боря', initB);
  await B.fill('#nameField', 'Боря'); await B.click('#modalBtns .btn:not(.ghost)'); await B.waitForTimeout(1500);
  const bText = await B.textContent('#meId'); console.log('B me row:', bText); const bId = (bText.match(/ID (\d+)/) || [])[1];
  const aId = (await A.textContent('#meId')).match(/ID (\d+)/)[1];
  console.log('ids A/B:', aId, bId);
  // A finds B and sends a request
  await A.click('#mFriends'); await A.waitForTimeout(1200);
  await A.click('.tab[data-tab="search"]'); await A.fill('#findId', bId); await A.click('#findGo'); await A.waitForTimeout(1500);
  console.log('A search result:', await A.textContent('#findOut'));
  await A.click('#findAct'); await A.waitForTimeout(1500);
  console.log('A after send:', await A.textContent('#findAct'));
  await shot(A, '05-search');
  await A.click('#panelClose');
  // B sees the badge and accepts
  await B.reload(); await B.waitForTimeout(2500);
  console.log('B friends badge:', await B.isVisible('#reqBadge'), await B.textContent('#reqBadge'));
  await B.click('#mFriends'); await B.waitForTimeout(1500); await shot(B, '06-requests');
  console.log('B requests:', (await B.textContent('#panelBody')).replace(/\s+/g, ' ').trim());
  await B.click('.mini.ok'); await B.waitForTimeout(1800);
  await B.click('.tab[data-tab="list"]'); await B.waitForTimeout(1500); await shot(B, '07-friends');
  console.log('B friends list:', (await B.textContent('#panelBody')).replace(/\s+/g, ' ').trim());
  // delete asks first
  await B.click('.row .mini.soft'); await B.waitForTimeout(300);
  console.log('B delete confirm:', await B.textContent('#modalTitle'), '|', await B.textContent('#modalText'));
  await shot(B, '08-confirm');
  await B.click('#modalBtns .btn.ghost'); await B.click('#panelClose');
  // scores, then the leaderboard
  await api(initA, 'score', { mode: 'endless', score: 640, secs: 70, bosses: 1 });
  await api(initB, 'score', { mode: 'endless', score: 910, secs: 90, bosses: 1 });
  await A.click('#mBoard'); await A.waitForTimeout(1600); await shot(A, '09-board');
  await A.click('.tab[data-tab="friends"]'); await A.waitForTimeout(1500); await shot(A, '10-board-friends');
  console.log('A friends board:', (await A.textContent('#panelBody')).replace(/\s+/g, ' ').trim());
  await A.click('#panelClose');
  // A invites B into a private room; B joins with the link from the bot
  let room = null;
  A.on('response', async r => { if (r.url().endsWith('/api/invite')) { try { room = (await r.json()).room; } catch (e) {} } });
  await A.click('#mPlay'); await A.click('#friendPlayBtn'); await A.waitForTimeout(1500);
  await A.click('#panelBody .row .mini'); await A.waitForTimeout(1500);
  console.log('A waiting:', await A.textContent('#waitTitle'), '| room', room);
  await shot(A, '11-wait-friend');
  const B2 = await mk('Боря', initB, '?room=' + room);
  await B2.waitForTimeout(2500);
  const ia = await A.evaluate(() => window.__popa.info()), ib = await B2.evaluate(() => window.__popa.info());
  console.log('paired:', ia.state, ib.state, '| mic buttons A/B:', await A.isVisible('#micBtn'), await B2.isVisible('#micBtn'), '| friend name on A:', await A.textContent('#mateName'));
  console.log(errs.join('\n') || 'no errors'); await b.close();
})();
