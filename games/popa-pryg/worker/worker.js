import html from './public/index.html';
import poster from './public/poster.jpg';

const GAME_URL = 'https://popa-pryg.giftstelegram01.workers.dev/';
const PLAY_BUTTON = { inline_keyboard: [[{ text: 'Играть', web_app: { url: GAME_URL } }]] };
const WELCOME =
  'Привет! Это «Попа-Прыг».\n\n' +
  'Попа сама прыгает по цилиндрам, а ты ведёшь её пальцем влево и вправо. ' +
  'Каждые 50 цилиндров ждёт босс, а на радужных цилиндрах с «?» прячутся сюрпризы.\n\n' +
  'Победи всех десятерых боссов и узнай, чья это попа. А в режиме «Онлайн» можно прыгать вместе с другом.\n\nЖми «Играть»!';

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
  out.description = await tg(env, 'setMyDescription', { description: 'Попа сама прыгает по цилиндрам, ты ведёшь её пальцем. 10 боссов, секретные цилиндры, игра вдвоём с другом и тайна в конце. Нажми «Старт», а потом «Играть».' });
  out.short = await tg(env, 'setMyShortDescription', { short_description: 'Прыгай по цилиндрам, побеждай боссов и узнай, чья это попа.' });
  return {
    bot: out.me.ok ? '@' + out.me.result.username : null,
    steps: Object.fromEntries(Object.entries(out).map(([k, v]) => [k, v.ok ? 'ok' : (v.description || 'failed')]))
  };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const json = (o, status = 200) => new Response(JSON.stringify(o, null, 2), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });

    if (url.pathname === '/' || url.pathname === '/index.html') {
      return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=60' } });
    }
    if (url.pathname === '/poster.jpg') {
      return new Response(poster, { headers: { 'content-type': 'image/jpeg', 'cache-control': 'public, max-age=86400' } });
    }
    if (url.pathname === '/ws') {
      if (request.headers.get('Upgrade') !== 'websocket') return new Response('expected websocket', { status: 426 });
      return env.LOBBY.get(env.LOBBY.idFromName('main')).fetch(request);
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

// Online lobby: the first player waits, the second one is paired with them, then every message is passed to the partner.
export class Lobby {
  constructor(state, env) { this.waiting = null; }
  async fetch(request) {
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    server.accept();
    server.partner = null; server.name = 'Друг';
    server.addEventListener('message', ev => this.onMessage(server, ev.data));
    const bye = () => this.onClose(server);
    server.addEventListener('close', bye);
    server.addEventListener('error', bye);
    return new Response(null, { status: 101, webSocket: client });
  }
  send(ws, m) { try { ws.send(typeof m === 'string' ? m : JSON.stringify(m)); } catch (e) {} }
  onMessage(ws, data) {
    if (typeof data !== 'string') {   // voice chunks: passed straight to the partner
      if (data && data.byteLength <= 4000 && ws.partner && ws.partner.readyState === 1) { try { ws.partner.send(data); } catch (e) {} }
      return;
    }
    if (data.length > 4000) return;
    let m; try { m = JSON.parse(data); } catch (e) { return; }
    if (m.t === 'hello' && !ws.hello) {
      ws.hello = true;
      ws.name = String(m.name || 'Друг').slice(0, 16);
      const other = this.waiting;
      if (other && other !== ws && other.readyState === 1) {
        this.waiting = null;
        other.partner = ws; ws.partner = other;
        const seed = Math.floor(Math.random() * 4294967296);
        this.send(other, { t: 'start', host: true, seed, name: ws.name });
        this.send(ws, { t: 'start', host: false, seed, name: other.name });
      } else {
        this.waiting = ws;
        this.send(ws, { t: 'wait' });
      }
      return;
    }
    if (ws.partner && ws.partner.readyState === 1) this.send(ws.partner, data);
  }
  onClose(ws) {
    if (ws.closedOnce) return; ws.closedOnce = true;
    if (this.waiting === ws) this.waiting = null;
    const p = ws.partner;
    if (p) { p.partner = null; this.send(p, { t: 'left' }); }
  }
}
