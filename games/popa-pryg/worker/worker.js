import html from './public/index.html';
import poster from './public/poster.jpg';

const GAME_URL = 'https://popa-pryg.giftstelegram01.workers.dev/';
const PLAY_BUTTON = { inline_keyboard: [[{ text: 'Играть', web_app: { url: GAME_URL } }]] };
const WELCOME =
  'Привет! Это «Попа-Прыг».\n\n' +
  'Попа сама прыгает по цилиндрам, а ты ведёшь её пальцем влево и вправо. ' +
  'Каждые 50 цилиндров ждёт босс, а на радужных цилиндрах с «?» прячутся сюрпризы.\n\n' +
  'Победи всех десятерых боссов и узнай, чья это попа. В «Бесконечном» режиме бейся за место в лидерборде, а в «Онлайне» прыгай вместе с другом.\n\nЖми «Играть»!';

// ---------- Telegram helpers ----------

// The webhook secret is derived from the bot token, so it never has to be stored anywhere else.
async function hookSecret(token) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('popa-pryg-hook:' + token));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

async function tg(env, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body || {})
  });
  const j = await r.json().catch(() => ({ ok: false, description: 'bad response' }));
  return { ok: !!j.ok, description: j.description, result: j.result };
}

async function hmac(key, data) {
  const k = await crypto.subtle.importKey('raw', typeof key === 'string' ? new TextEncoder().encode(key) : key, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', k, new TextEncoder().encode(data)));
}
const hex = a => [...a].map(b => b.toString(16).padStart(2, '0')).join('');

// Checks the signature Telegram puts on Mini App launch data, so nobody can pretend to be another player.
async function verifyInitData(initData, botToken) {
  if (!initData || !botToken) return null;
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  if (!hash) return null;
  params.delete('hash');
  const check = [...params.entries()].sort(([a], [b]) => (a < b ? -1 : 1)).map(([k, v]) => `${k}=${v}`).join('\n');
  const secret = await hmac('WebAppData', botToken);
  if (hex(await hmac(secret, check)) !== hash) return null;
  const authDate = +params.get('auth_date') || 0;
  if (Date.now() / 1000 - authDate > 7 * 86400) return null;
  let user = null;
  try { user = JSON.parse(params.get('user') || 'null'); } catch (e) {}
  if (!user || !user.id) return null;
  return { id: user.id, first: String(user.first_name || '').slice(0, 64) };
}

async function onUpdate(env, update) {
  const msg = update.message;
  if (!msg || !msg.chat) return;
  const text = (msg.text || '').trim();
  if (text.startsWith('/start') || text.startsWith('/play')) {
    const r = await tg(env, 'sendPhoto', { chat_id: msg.chat.id, photo: GAME_URL + 'poster.jpg?v=1', caption: WELCOME, reply_markup: PLAY_BUTTON });
    if (!r.ok) await tg(env, 'sendMessage', { chat_id: msg.chat.id, text: WELCOME, reply_markup: PLAY_BUTTON });
  } else {
    await tg(env, 'sendMessage', { chat_id: msg.chat.id, text: 'Нажми «Играть», чтобы открыть игру.', reply_markup: PLAY_BUTTON });
  }
}

// One-time bot setup: webhook, menu button, commands and descriptions. Safe to call again; it only sets fixed values.
async function setup(env, origin) {
  const secret = await hookSecret(env.TELEGRAM_BOT_TOKEN);
  const out = {};
  out.me = await tg(env, 'getMe');
  out.webhook = await tg(env, 'setWebhook', { url: origin + '/telegram', secret_token: secret, allowed_updates: ['message'], drop_pending_updates: true });
  out.menu = await tg(env, 'setChatMenuButton', { menu_button: { type: 'web_app', text: 'Играть', web_app: { url: GAME_URL } } });
  out.commands = await tg(env, 'setMyCommands', { commands: [{ command: 'start', description: 'Начать игру' }, { command: 'play', description: 'Открыть игру' }] });
  out.description = await tg(env, 'setMyDescription', { description: 'Попа сама прыгает по цилиндрам, ты ведёшь её пальцем. 10 боссов, особые цилиндры, бесконечный режим с лидербордом, игра с друзьями и тайна в конце. Нажми «Старт», а потом «Играть».' });
  out.short = await tg(env, 'setMyShortDescription', { short_description: 'Прыгай по цилиндрам, побеждай боссов и узнай, чья это попа.' });
  return {
    bot: out.me.ok ? '@' + out.me.result.username : null,
    steps: Object.fromEntries(Object.entries(out).map(([k, v]) => [k, v.ok ? 'ok' : (v.description || 'failed')]))
  };
}

// ---------- the Worker ----------

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });

    if (url.pathname === '/' || url.pathname === '/index.html') {
      return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=60' } });
    }
    if (url.pathname === '/poster.jpg') {
      return new Response(poster, { headers: { 'content-type': 'image/jpeg', 'cache-control': 'public, max-age=86400' } });
    }
    if (url.pathname.startsWith('/music/') && /^\/music\/[a-z0-9-]+\.mp3$/.test(url.pathname)) {
      // tracks are stored in KV; the edge cache keeps KV reads low
      const cache = caches.default, hit = await cache.match(request);
      if (hit) return hit;
      const data = env.MEDIA && await env.MEDIA.get(url.pathname.slice(1), 'arrayBuffer');
      if (!data) return new Response('not found', { status: 404 });
      const res = new Response(data, { headers: { 'content-type': 'audio/mpeg', 'cache-control': 'public, max-age=604800, immutable' } });
      ctx.waitUntil(cache.put(request, res.clone()));
      return res;
    }
    if (url.pathname === '/stats') {
      const res = await env.ACCOUNTS.get(env.ACCOUNTS.idFromName('main')).fetch('https://accounts/op', { method: 'POST', body: JSON.stringify({ op: 'stats' }) });
      return new Response(JSON.stringify(await res.json(), null, 2), { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
    }
    if (url.pathname === '/ws') {
      if (request.headers.get('Upgrade') !== 'websocket') return new Response('expected websocket', { status: 426 });
      return env.LOBBY.get(env.LOBBY.idFromName('main')).fetch(request);
    }
    if (url.pathname.startsWith('/api/') && request.method === 'POST') {
      const who = await verifyInitData(request.headers.get('X-Tg-Init'), env.TELEGRAM_BOT_TOKEN);
      if (!who) return json({ ok: false, error: 'auth' }, 401);
      const body = await request.json().catch(() => ({}));
      const op = url.pathname.slice(5);
      const res = await env.ACCOUNTS.get(env.ACCOUNTS.idFromName('main')).fetch('https://accounts/op', {
        method: 'POST', body: JSON.stringify({ op, who, body })
      });
      const out = await res.json();
      // messages the bot sends on the player's behalf: friend requests and game invites
      if (out.notify) {
        const n = out.notify; delete out.notify;
        const sent = await tg(env, 'sendMessage', { chat_id: n.chat, text: n.text, reply_markup: { inline_keyboard: [[{ text: n.button, web_app: { url: GAME_URL + (n.query || '') } }]] } });
        out.delivered = sent.ok;
      }
      return json(out, res.status);
    }
    if (url.pathname === '/telegram' && request.method === 'POST') {
      if (!env.TELEGRAM_BOT_TOKEN) return new Response('no token', { status: 503 });
      const got = request.headers.get('X-Telegram-Bot-Api-Secret-Token');
      if (got !== await hookSecret(env.TELEGRAM_BOT_TOKEN)) return new Response('forbidden', { status: 403 });
      const update = await request.json().catch(() => null);
      if (update) ctx.waitUntil(onUpdate(env, update));
      return new Response('ok');
    }
    if (url.pathname === '/setup') {
      if (!env.TELEGRAM_BOT_TOKEN) return json({ ok: false, error: 'TELEGRAM_BOT_TOKEN is not set on this Worker' }, 503);
      return json(await setup(env, url.origin));
    }
    return new Response('Not found', { status: 404 });
  }
};

// ---------- names ----------

const BAD_ROOTS = ['хуй', 'хуе', 'хуя', 'хуи', 'пизд', 'ебат', 'ебан', 'ебал', 'ебуч', 'еблан', 'бляд', 'блят', 'сука', 'суки', 'мудак', 'мудил', 'пидор', 'пидар', 'педик', 'шлюх', 'гандон', 'залуп', 'дрочи',
  'fuck', 'shit', 'bitch', 'cunt', 'nigger', 'nigga', 'faggot', 'whore', 'dick', 'pussy'];
const LOOKALIKE = { a: 'а', e: 'е', o: 'о', p: 'р', c: 'с', x: 'х', y: 'у', k: 'к', m: 'м', t: 'т', h: 'н', b: 'в', '0': 'о', '3': 'з', '6': 'б', 'ё': 'е' };
function isRude(name) {
  const low = name.toLowerCase();
  const plain = low.replace(/[^\p{L}\p{N}]/gu, '');
  const cyr = [...plain].map(ch => LOOKALIKE[ch] || ch).join('');
  return BAD_ROOTS.some(r => plain.includes(r) || cyr.includes(r));
}
// Any letters, digits, symbols and emoji; at most 24 visible characters; invisible and control characters removed.
function cleanName(raw) {
  let s = String(raw || '').normalize('NFC')
    .replace(/[\u0000-\u001F\u007F-\u009F­​‌‎‏‪-‮⁠-⁤⁦-⁩﻿]/g, '')
    .replace(/\s+/g, ' ').trim().replace(/^\u200D+|\u200D+$/g, '').trim()
    .replace(/(\p{M}{2})\p{M}+/gu, '$1');
  const chars = [...new Intl.Segmenter('ru', { granularity: 'grapheme' }).segment(s)];
  if (!chars.length) return { error: 'Имя не может быть пустым' };
  if (chars.length > 24) return { error: 'Не больше 24 символов' };
  if (isRude(s)) return { error: 'Такое имя нельзя, выбери другое' };
  return { name: s };
}

const weekKey = t => Math.floor((t + 3 * 3600e3 + 3 * 86400e3) / 604800e3);   // weeks start on Monday 00:00 Moscow time
const dayKey = t => Math.floor((t + 3 * 3600e3) / 86400e3);                       // days start at 00:00 Moscow time

// ---------- economy: coins, experience, levels, upgrades ----------
// level L needs round(100 * L^1.5) xp to reach L + 1; every new level pays 20 * L coins
const xpNeed = L => Math.round(100 * Math.pow(L, 1.5));
function levelInfo(xp) {
  let L = 1, left = Math.max(0, xp);
  while (left >= xpNeed(L) && L < 999) { left -= xpNeed(L); L++; }
  return { level: L, into: left, need: xpNeed(L) };
}
const UPGRADES = { piggy: 5, shield: 5, luck: 5 };   // id -> max level (the magnet was removed; its coins are given back)
const UPG_COST = [60, 150, 350, 800, 1600];                      // price of level 1..5
const readUpg = u => { try { const o = JSON.parse(u.upg || '{}'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } };
function econ(u) {
  const li = levelInfo(u.xp || 0);
  return { coins: u.coins || 0, xp: u.xp || 0, level: li.level, levelInto: li.into, levelNeed: li.need, upg: readUpg(u) };
}

// ---------- accounts: profiles, IDs, scores, friends (one Durable Object with SQLite) ----------

export class Accounts {
  constructor(state, env) {
    this.sql = state.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS users (tg INTEGER PRIMARY KEY, uid INTEGER UNIQUE, name TEXT, avatar INTEGER, first TEXT, created INTEGER,
        best INTEGER DEFAULT 0, best_at INTEGER DEFAULT 0, story INTEGER DEFAULT 0, bosses INTEGER DEFAULT 0, games INTEGER DEFAULT 0);
      CREATE TABLE IF NOT EXISTS counters (k TEXT PRIMARY KEY, v INTEGER);
      CREATE TABLE IF NOT EXISTS weekly (uid INTEGER, week INTEGER, best INTEGER, at INTEGER, PRIMARY KEY (uid, week));
      CREATE TABLE IF NOT EXISTS requests (src INTEGER, dst INTEGER, at INTEGER, PRIMARY KEY (src, dst));
      CREATE TABLE IF NOT EXISTS friends (a INTEGER, b INTEGER, at INTEGER, PRIMARY KEY (a, b));
      CREATE INDEX IF NOT EXISTS users_best ON users (best DESC);
      CREATE INDEX IF NOT EXISTS weekly_best ON weekly (week, best DESC);
      CREATE INDEX IF NOT EXISTS requests_dst ON requests (dst);
      CREATE TABLE IF NOT EXISTS daily (uid INTEGER, day INTEGER, best INTEGER, at INTEGER, PRIMARY KEY (uid, day));
      CREATE INDEX IF NOT EXISTS daily_best ON daily (day, best DESC);
      CREATE TABLE IF NOT EXISTS deaths (day INTEGER, mode TEXT, bucket INTEGER, boss INTEGER, reason TEXT, n INTEGER, PRIMARY KEY (day, mode, bucket, boss, reason));
    `);
    try { this.sql.exec('ALTER TABLE users ADD COLUMN seen INTEGER DEFAULT 0'); } catch (e) {}
    for (const col of ['coins INTEGER DEFAULT 0', 'xp INTEGER DEFAULT 0', 'level INTEGER DEFAULT 1', "upg TEXT DEFAULT '{}'"])
      try { this.sql.exec('ALTER TABLE users ADD COLUMN ' + col); } catch (e) {}
  }
  rows(q, ...b) { return this.sql.exec(q, ...b).toArray(); }
  row(q, ...b) { return this.rows(q, ...b)[0] || null; }
  userByTg(tg) { return this.row('SELECT * FROM users WHERE tg = ?', tg); }
  userByUid(uid) { return this.row('SELECT * FROM users WHERE uid = ?', uid); }
  pub(u) { return u ? { uid: u.uid, name: u.name, avatar: u.avatar } : null; }
  isFriend(a, b) { return !!this.row('SELECT 1 AS x FROM friends WHERE a = ? AND b = ?', a, b); }
  makeFriends(a, b) {
    const t = Date.now();
    this.sql.exec('INSERT OR IGNORE INTO friends (a, b, at) VALUES (?, ?, ?)', a, b, t);
    this.sql.exec('INSERT OR IGNORE INTO friends (a, b, at) VALUES (?, ?, ?)', b, a, t);
    this.sql.exec('DELETE FROM requests WHERE (src = ? AND dst = ?) OR (src = ? AND dst = ?)', a, b, b, a);
  }

  stats() {
    // where players fall, over the last 7 days: by distance, by boss and by reason
    const from = dayKey(Date.now()) - 6;
    return {
      ok: true, days: 7,
      players: this.row('SELECT COUNT(*) AS n FROM users WHERE uid IS NOT NULL').n,
      byDistance: this.rows('SELECT mode, bucket * 25 AS from_row, SUM(n) AS deaths FROM deaths WHERE day >= ? GROUP BY mode, bucket ORDER BY mode, bucket', from),
      byBoss: this.rows('SELECT mode, boss + 1 AS boss, SUM(n) AS deaths FROM deaths WHERE day >= ? AND boss >= 0 GROUP BY mode, boss ORDER BY deaths DESC', from),
      byReason: this.rows('SELECT reason, SUM(n) AS deaths FROM deaths WHERE day >= ? GROUP BY reason ORDER BY deaths DESC LIMIT 20', from)
    };
  }

  async fetch(request) {
    const { op, who, body } = await request.json();
    const send = (o, status = 200) => new Response(JSON.stringify(o), { status });
    if (op === 'stats') return send(this.stats());
    // every call makes sure the player has a row; the game ID comes only with a name
    this.sql.exec('INSERT OR IGNORE INTO users (tg, first, created) VALUES (?, ?, ?)', who.id, who.first, Date.now());
    this.sql.exec('UPDATE users SET seen = ? WHERE tg = ?', Date.now(), who.id);
    let me = this.userByTg(who.id);
    { const u = readUpg(me); if (u.magnet) { let back = 0; for (let k = 0; k < Math.min(5, u.magnet); k++) back += UPG_COST[k]; delete u.magnet;
      this.sql.exec('UPDATE users SET coins = coins + ?, upg = ? WHERE tg = ?', back, JSON.stringify(u), who.id); me = this.userByTg(who.id); } }
    const needName = () => send({ ok: false, error: 'noname' }, 400);
    const b = body || {};

    if (op === 'me') {
      const incoming = me.uid ? this.row('SELECT COUNT(*) AS n FROM requests WHERE dst = ?', me.uid).n : 0;
      const wk = me.uid ? this.row('SELECT best FROM weekly WHERE uid = ? AND week = ?', me.uid, weekKey(Date.now())) : null;
      const dy = me.uid ? this.row('SELECT best FROM daily WHERE uid = ? AND day = ?', me.uid, dayKey(Date.now())) : null;
      return send({ ok: true, me: { uid: me.uid, name: me.name, avatar: me.avatar, best: me.best, weekBest: wk ? wk.best : 0, dayBest: dy ? dy.best : 0, story: !!me.story, bosses: me.bosses, games: me.games, ...econ(me) }, upgCost: UPG_COST, upgMax: UPGRADES, incoming, day: dayKey(Date.now()) });
    }
    if (op === 'ping') return send({ ok: true });

    if (op === 'name') {
      const c = cleanName(b.name);
      if (c.error) return send({ ok: false, error: c.error }, 400);
      if (!me.uid) {
        const n = this.row("INSERT INTO counters (k, v) VALUES ('uid', 1) ON CONFLICT (k) DO UPDATE SET v = v + 1 RETURNING v").v;
        this.sql.exec('UPDATE users SET uid = ?, avatar = ? WHERE tg = ?', n, Math.floor(Math.random() * 2147483647), who.id);
      }
      this.sql.exec('UPDATE users SET name = ? WHERE tg = ?', c.name, who.id);
      me = this.userByTg(who.id);
      return send({ ok: true, me: this.pub(me) });
    }

    if (op === 'avatar') {
      if (!me.uid) return needName();
      this.sql.exec('UPDATE users SET avatar = ? WHERE tg = ?', Math.floor(Math.random() * 2147483647), who.id);
      return send({ ok: true, me: this.pub(this.userByTg(who.id)) });
    }

    if (op === 'score') {
      // every finished game counts for the profile; only honest endless runs go to the leaderboard
      const score = Math.max(0, Math.floor(+b.score || 0)), secs = Math.max(0, +b.secs || 0), bosses = Math.max(0, Math.min(500, Math.floor(+b.bosses || 0)));
      this.sql.exec('UPDATE users SET games = games + 1, bosses = bosses + ? WHERE tg = ?', bosses, who.id);
      if (b.mode === 'story' && b.finished) this.sql.exec('UPDATE users SET story = 1 WHERE tg = ?', who.id);
      if (!b.finished && Number.isFinite(+b.row)) {
        const mode = ['story', 'endless', 'daily', 'online'].includes(b.mode) ? b.mode : 'other';
        const boss = Number.isFinite(+b.boss) ? Math.max(-1, Math.min(9, Math.floor(+b.boss))) : -1;
        const reason = String(b.reason || '').slice(0, 40);
        this.sql.exec('INSERT INTO deaths (day, mode, bucket, boss, reason, n) VALUES (?, ?, ?, ?, ?, 1) ON CONFLICT (day, mode, bucket, boss, reason) DO UPDATE SET n = n + 1',
          dayKey(Date.now()), mode, Math.max(0, Math.floor(+b.row / 25)), boss, reason);
      }
      const plausible = secs >= 5 && score <= secs * 35 + bosses * 1500 + 300;
      const today = dayKey(Date.now());
      // coins and experience: only for honest runs without the autopilot; coins picked up are capped by run time
      let eco = { earned: 0, xpGained: 0, levelUp: 0, reward: 0 };
      if (plausible && !b.auto) {
        const upg = readUpg(me);
        const picked = Math.max(0, Math.min(Math.floor(+b.coins || 0), Math.floor(secs * 0.7) + 5));
        const bags = Math.max(0, Math.min(Math.floor(+b.bags || 0), Math.floor(secs / 90) + 1));   // sacks of 50: rare, at most one per 1.5 minutes
        let earned = Math.round((picked + 50 * bags) * (1 + 0.1 * Math.min(5, upg.piggy || 0))) + bosses * 10;
        if (b.mode === 'daily' && me.uid && !this.row('SELECT 1 AS x FROM daily WHERE uid = ? AND day = ?', me.uid, today)) earned += 25;   // first daily try of the day
        const xpGained = score + bosses * 50;
        const before = levelInfo(me.xp || 0).level, after = levelInfo((me.xp || 0) + xpGained).level;
        let reward = 0; for (let L = before + 1; L <= after; L++) reward += 20 * (L - 1);
        this.sql.exec('UPDATE users SET coins = coins + ?, xp = xp + ?, level = ? WHERE tg = ?', earned + reward, xpGained, after, who.id);
        eco = { earned, xpGained, levelUp: after > before ? after : 0, reward };
        me = this.userByTg(who.id);
      }
      eco = { ...eco, ...econ(me) };
      if (b.mode === 'daily' && !b.auto && plausible && me.uid && (+b.day === today || +b.day === today - 1)) {
        const cur = this.row('SELECT best FROM daily WHERE uid = ? AND day = ?', me.uid, +b.day);
        const newDay = !cur || score > cur.best;
        if (newDay) this.sql.exec('INSERT INTO daily (uid, day, best, at) VALUES (?, ?, ?, ?) ON CONFLICT (uid, day) DO UPDATE SET best = excluded.best, at = excluded.at', me.uid, +b.day, score, Date.now());
        const r = this.row('SELECT best, at FROM daily WHERE uid = ? AND day = ?', me.uid, +b.day);
        const place = this.row('SELECT COUNT(*) + 1 AS p FROM daily WHERE day = ? AND (best > ? OR (best = ? AND at < ?))', +b.day, r.best, r.best, r.at).p;
        return send({ ok: true, counted: true, newBest: newDay, best: r.best, place, eco });
      }
      const counts = b.mode === 'endless' && !b.auto && plausible && me.uid;
      let newBest = false, newWeek = false;
      if (counts) {
        if (score > me.best) { this.sql.exec('UPDATE users SET best = ?, best_at = ? WHERE tg = ?', score, Date.now(), who.id); newBest = true; }
        const wk = weekKey(Date.now());
        const cur = this.row('SELECT best FROM weekly WHERE uid = ? AND week = ?', me.uid, wk);
        if (!cur || score > cur.best) { this.sql.exec('INSERT INTO weekly (uid, week, best, at) VALUES (?, ?, ?, ?) ON CONFLICT (uid, week) DO UPDATE SET best = excluded.best, at = excluded.at', me.uid, wk, score, Date.now()); newWeek = true; }
      }
      me = this.userByTg(who.id);
      const place = counts && me.best > 0 ? this.row('SELECT COUNT(*) + 1 AS p FROM users WHERE uid IS NOT NULL AND best > ?', me.best).p : null;
      return send({ ok: true, eco, counted: !!counts, why: !['endless', 'daily'].includes(b.mode) ? 'mode' : b.auto ? 'auto' : !me.uid ? 'noname' : !plausible ? 'check' : b.mode === 'daily' ? 'day' : null, newBest, newWeek, best: me.best, place });
    }

    if (op === 'upgrade') {
      const id = String(b.id || '');
      if (!(id in UPGRADES)) return send({ ok: false, error: 'Нет такого улучшения' }, 400);
      const upg = readUpg(me), lv = Math.min(UPGRADES[id], Math.max(0, Math.floor(upg[id] || 0)));
      if (lv >= UPGRADES[id]) return send({ ok: false, error: 'Уже максимум' }, 400);
      const cost = UPG_COST[lv];
      if ((me.coins || 0) < cost) return send({ ok: false, error: 'Не хватает попкоинов' }, 400);
      upg[id] = lv + 1;
      this.sql.exec('UPDATE users SET coins = coins - ?, upg = ? WHERE tg = ? AND coins >= ?', cost, JSON.stringify(upg), who.id, cost);
      return send({ ok: true, ...econ(this.userByTg(who.id)) });
    }

    if (op === 'leaderboard') {
      const scope = ['week', 'friends', 'day'].includes(b.scope) ? b.scope : 'all';
      let top, mine = null;
      if (scope === 'day') {
        const dk = dayKey(Date.now());
        top = this.rows('SELECT u.uid, u.name, u.avatar, u.level, d.best AS score FROM daily d JOIN users u ON u.uid = d.uid WHERE d.day = ? AND u.name IS NOT NULL ORDER BY d.best DESC, d.at ASC LIMIT 50', dk);
        if (me.uid) { const r = this.row('SELECT best, at FROM daily WHERE uid = ? AND day = ?', me.uid, dk); if (r) mine = { score: r.best, place: this.row('SELECT COUNT(*) + 1 AS p FROM daily WHERE day = ? AND (best > ? OR (best = ? AND at < ?))', dk, r.best, r.best, r.at).p }; }
      } else if (scope === 'week') {
        const wk = weekKey(Date.now());
        top = this.rows('SELECT u.uid, u.name, u.avatar, u.level, w.best AS score FROM weekly w JOIN users u ON u.uid = w.uid WHERE w.week = ? AND u.name IS NOT NULL ORDER BY w.best DESC, w.at ASC LIMIT 50', wk);
        if (me.uid) { const r = this.row('SELECT best, at FROM weekly WHERE uid = ? AND week = ?', me.uid, wk); if (r) mine = { score: r.best, place: this.row('SELECT COUNT(*) + 1 AS p FROM weekly WHERE week = ? AND (best > ? OR (best = ? AND at < ?))', wk, r.best, r.best, r.at).p }; }
      } else if (scope === 'friends') {
        if (!me.uid) return needName();
        top = this.rows('SELECT u.uid, u.name, u.avatar, u.level, u.best AS score FROM users u WHERE u.uid = ? OR u.uid IN (SELECT b FROM friends WHERE a = ?) ORDER BY u.best DESC, u.best_at ASC LIMIT 100', me.uid, me.uid);
        const i = top.findIndex(r => r.uid === me.uid); if (i >= 0) mine = { score: top[i].score, place: i + 1 };
      } else {
        top = this.rows('SELECT uid, name, avatar, level, best AS score FROM users WHERE uid IS NOT NULL AND name IS NOT NULL AND best > 0 ORDER BY best DESC, best_at ASC LIMIT 50');
        if (me.uid && me.best > 0) mine = { score: me.best, place: this.row('SELECT COUNT(*) + 1 AS p FROM users WHERE uid IS NOT NULL AND (best > ? OR (best = ? AND best_at < ?))', me.best, me.best, me.best_at).p };
      }
      return send({ ok: true, scope, top: top.map((r, i) => ({ place: i + 1, uid: r.uid, name: r.name, avatar: r.avatar, level: r.level || 1, score: r.score })), mine, myUid: me.uid });
    }

    if (!me.uid) return needName();

    if (op === 'find') {
      const uid = Math.floor(+b.uid || 0);
      const u = uid > 0 ? this.userByUid(uid) : null;
      if (!u) return send({ ok: false, error: 'Игрока с таким ID нет' }, 404);
      let rel = 'none';
      if (u.uid === me.uid) rel = 'self';
      else if (this.isFriend(me.uid, u.uid)) rel = 'friend';
      else if (this.row('SELECT 1 AS x FROM requests WHERE src = ? AND dst = ?', me.uid, u.uid)) rel = 'sent';
      else if (this.row('SELECT 1 AS x FROM requests WHERE src = ? AND dst = ?', u.uid, me.uid)) rel = 'incoming';
      return send({ ok: true, user: { ...this.pub(u), best: u.best }, rel });
    }

    if (op === 'request') {
      const u = this.userByUid(Math.floor(+b.uid || 0));
      if (!u) return send({ ok: false, error: 'Игрока с таким ID нет' }, 404);
      if (u.uid === me.uid) return send({ ok: false, error: 'Это ты' }, 400);
      if (this.isFriend(me.uid, u.uid)) return send({ ok: true, rel: 'friend' });
      if (this.row('SELECT 1 AS x FROM requests WHERE src = ? AND dst = ?', u.uid, me.uid)) { this.makeFriends(me.uid, u.uid); return send({ ok: true, rel: 'friend' }); }
      const fresh = !this.row('SELECT 1 AS x FROM requests WHERE src = ? AND dst = ?', me.uid, u.uid);
      this.sql.exec('INSERT OR IGNORE INTO requests (src, dst, at) VALUES (?, ?, ?)', me.uid, u.uid, Date.now());
      const out = { ok: true, rel: 'sent' };
      if (fresh) out.notify = { chat: u.tg, text: `${me.name} (ID ${me.uid}) хочет добавить тебя в друзья в «Попа-Прыг».`, button: 'Открыть заявки', query: '?tab=requests' };
      return send(out);
    }

    if (op === 'requests') {
      const list = this.rows('SELECT u.uid, u.name, u.avatar, r.at FROM requests r JOIN users u ON u.uid = r.src WHERE r.dst = ? ORDER BY r.at DESC LIMIT 100', me.uid);
      return send({ ok: true, list, now: Date.now() });
    }

    if (op === 'respond') {
      const uid = Math.floor(+b.uid || 0);
      if (!this.row('SELECT 1 AS x FROM requests WHERE src = ? AND dst = ?', uid, me.uid)) return send({ ok: false, error: 'Заявки уже нет' }, 404);
      if (b.accept) this.makeFriends(me.uid, uid);
      else this.sql.exec('DELETE FROM requests WHERE src = ? AND dst = ?', uid, me.uid);
      return send({ ok: true });
    }

    if (op === 'friends') {
      const list = this.rows('SELECT u.uid, u.name, u.avatar, u.best, u.seen FROM friends f JOIN users u ON u.uid = f.b WHERE f.a = ? ORDER BY u.seen DESC LIMIT 500', me.uid);
      return send({ ok: true, list, now: Date.now() });
    }

    if (op === 'unfriend') {
      const uid = Math.floor(+b.uid || 0);
      this.sql.exec('DELETE FROM friends WHERE (a = ? AND b = ?) OR (a = ? AND b = ?)', me.uid, uid, uid, me.uid);
      return send({ ok: true });
    }

    if (op === 'invite') {
      const u = this.userByUid(Math.floor(+b.uid || 0));
      if (!u || !this.isFriend(me.uid, u.uid)) return send({ ok: false, error: 'Это не твой друг' }, 400);
      const room = [...crypto.getRandomValues(new Uint8Array(6))].map(x => 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[x % 32]).join('');
      return send({ ok: true, room, notify: { chat: u.tg, text: `${me.name} (ID ${me.uid}) зовёт тебя прыгать вместе в «Попа-Прыг»! Приглашение действует, пока он ждёт.`, button: 'Прыгать вместе', query: '?room=' + room } });
    }

    return send({ ok: false, error: 'unknown' }, 404);
  }
}

// ---------- online lobby: random pairs, private rooms for friends, and coming back after a short drop ----------

const RESUME_MS = 15000;
export class Lobby {
  constructor(state, env) { this.waiting = null; this.rooms = new Map(); this.lost = new Map(); }
  async fetch(request) {
    const url = new URL(request.url);
    const room = (url.searchParams.get('room') || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12);
    const resume = (url.searchParams.get('resume') || '').replace(/[^a-z0-9]/g, '').slice(0, 32);
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    server.accept();
    server.partner = null; server.name = 'Друг'; server.room = room || null;
    server.addEventListener('message', ev => this.onMessage(server, ev.data));
    const bye = () => this.onClose(server);
    server.addEventListener('close', bye);
    server.addEventListener('error', bye);
    if (resume) this.resume(server, resume);
    return new Response(null, { status: 101, webSocket: client });
  }
  send(ws, m) { try { ws.send(typeof m === 'string' ? m : JSON.stringify(m)); } catch (e) {} }
  token() { return [...crypto.getRandomValues(new Uint8Array(12))].map(b => b.toString(16).padStart(2, '0')).join(''); }
  pairUp(a, b) {
    a.partner = b; b.partner = a;
    a.token = this.token(); b.token = this.token();
    const seed = Math.floor(Math.random() * 4294967296), voice = !!a.room;
    this.send(a, { t: 'start', host: true, seed, name: b.name, avatar: b.avatar, voice, token: a.token });
    this.send(b, { t: 'start', host: false, seed, name: a.name, avatar: a.avatar, voice, token: b.token });
  }
  resume(ws, token) {
    const old = this.lost.get(token);
    if (!old) { this.send(ws, { t: 'resume-failed' }); return; }
    this.lost.delete(token); clearTimeout(old.timer);
    const p = old.partner;
    ws.hello = true; ws.name = old.name; ws.avatar = old.avatar; ws.room = old.room; ws.token = token;
    if (p && p.readyState === 1 && !p.closedOnce) { ws.partner = p; p.partner = ws; this.send(p, { t: 'back' }); this.send(ws, { t: 'resumed' }); }
    else this.send(ws, { t: 'resume-failed' });
  }
  onMessage(ws, data) {
    if (typeof data !== 'string') {   // voice chunks: only between friends in a private room
      if (ws.room && data && data.byteLength <= 4000 && ws.partner && ws.partner.readyState === 1) { try { ws.partner.send(data); } catch (e) {} }
      return;
    }
    if (data.length > 4000) return;
    let m; try { m = JSON.parse(data); } catch (e) { return; }
    if (m.t === 'hello' && !ws.hello) {
      ws.hello = true;
      ws.name = String(m.name || 'Друг').slice(0, 40);
      ws.avatar = Number.isFinite(+m.avatar) ? +m.avatar : null;
      if (ws.room) {
        const other = this.rooms.get(ws.room);
        if (other && other !== ws && other.readyState === 1 && !other.partner) { this.rooms.delete(ws.room); this.pairUp(other, ws); }
        else { this.rooms.set(ws.room, ws); this.send(ws, { t: 'wait' }); }
        return;
      }
      const other = this.waiting;
      if (other && other !== ws && other.readyState === 1) { this.waiting = null; this.pairUp(other, ws); }
      else { this.waiting = ws; this.send(ws, { t: 'wait' }); }
      return;
    }
    if (m.t === 'bye') { ws.leaving = true; return; }
    if (ws.partner && ws.partner.readyState === 1) this.send(ws.partner, data);
  }
  onClose(ws) {
    if (ws.closedOnce) return; ws.closedOnce = true;
    try { ws.close(1000, 'bye'); } catch (e) {}   // finish the closing handshake so the phone knows at once
    if (this.waiting === ws) this.waiting = null;
    if (ws.room && this.rooms.get(ws.room) === ws) this.rooms.delete(ws.room);
    const p = ws.partner;
    if (!p) return;
    if (ws.leaving || !ws.token) { p.partner = null; this.send(p, { t: 'left' }); return; }
    // the connection dropped: keep the seat for a while so the player can come back
    this.send(p, { t: 'lag' });
    const entry = { partner: p, name: ws.name, avatar: ws.avatar, room: ws.room };
    entry.timer = setTimeout(() => { if (this.lost.get(ws.token) === entry) { this.lost.delete(ws.token); if (p.partner === ws) { p.partner = null; this.send(p, { t: 'left' }); } } }, RESUME_MS);
    this.lost.set(ws.token, entry);
  }
}
