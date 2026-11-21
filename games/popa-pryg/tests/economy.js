// Coins, experience, levels and upgrades on a test Worker. Usage: BOT_TOKEN=... node economy.js https://popa-pryg-test....workers.dev
const crypto = require('crypto');
const BASE = process.argv[2], TOKEN = process.env.BOT_TOKEN;
const sign = (id, first) => {
  const p = new URLSearchParams({ auth_date: String(Math.floor(Date.now() / 1000)), query_id: 'q' + id, user: JSON.stringify({ id, first_name: first }) });
  const check = [...p.entries()].sort(([a], [b]) => a < b ? -1 : 1).map(([k, v]) => `${k}=${v}`).join('\n');
  const secret = crypto.createHmac('sha256', 'WebAppData').update(TOKEN).digest();
  p.set('hash', crypto.createHmac('sha256', secret).update(check).digest('hex'));
  return p.toString();
};
const call = async (who, op, body = {}) => {
  const r = await fetch(`${BASE}/api/${op}`, { method: 'POST', headers: { 'X-Tg-Init': who, 'content-type': 'application/json' }, body: JSON.stringify(body) });
  return { status: r.status, ...(await r.json()) };
};
(async () => {
  const A = sign(910000000 + Math.floor(Math.random() * 1e6), 'Эко');
  const out = (label, v) => console.log(label.padEnd(30), JSON.stringify(v));
  await call(A, 'name', { name: 'Эко-тест' });
  const m0 = (await call(A, 'me'));
  out('start', { coins: m0.me.coins, xp: m0.me.xp, level: m0.me.level, upg: m0.me.upg, cost: m0.upgCost });
  out('honest run 60s, 20 coins', (await call(A, 'score', { mode: 'endless', score: 400, secs: 60, bosses: 1, coins: 20 })).eco);
  out('greedy run 10s, 999 coins', (await call(A, 'score', { mode: 'endless', score: 100, secs: 10, bosses: 0, coins: 999 })).eco);
  out('autopilot run', (await call(A, 'score', { mode: 'endless', score: 300, secs: 40, bosses: 0, coins: 10, auto: true })).eco);
  out('impossible score', (await call(A, 'score', { mode: 'endless', score: 99999, secs: 10, bosses: 0, coins: 5 })).eco);
  out('buy piggy', await call(A, 'upgrade', { id: 'piggy' }));
  out('buy bogus', await call(A, 'upgrade', { id: 'gold' }));
  for (let k = 0; k < 6; k++) await call(A, 'score', { mode: 'story', score: 900, secs: 120, bosses: 3, coins: 40 });
  const m1 = (await call(A, 'me')).me;
  out('after 6 big runs', { coins: m1.coins, xp: m1.xp, level: m1.level, into: m1.levelInto, need: m1.levelNeed, upg: m1.upg });
  let r; for (let k = 0; k < 6; k++) r = await call(A, 'upgrade', { id: 'magnet' });
  out('magnet x6 (last)', r);
  out('daily first try bonus', (await call(A, 'score', { mode: 'daily', score: 200, secs: 40, bosses: 0, coins: 0, day: (await call(A, 'me')).day })).eco);
  const lb = await call(A, 'leaderboard', { scope: 'all' });
  out('leaderboard has level', lb.top.slice(0, 2));
})();
