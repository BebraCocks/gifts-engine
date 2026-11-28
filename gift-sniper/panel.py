"""Панель управления: бот из BotFather + мини-апп на этом же сервере.

- бот присылает уведомления и открывает мини-апп кнопкой меню «Панель»;
- мини-апп (panel.html) ходит в JSON API ниже; каждый запрос подписан
  Telegram (initData) и принимается только от наших аккаунтов.
Настройка: giftsniper-panel (токен бота и адрес вводятся на сервере).
"""

import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl import functions, types

import bot as core

HERE = Path(__file__).parent
PORT = 8088
MAX_AGE = 24 * 3600          # подпись initData действительна сутки


def check_init_data(init_data, token):
    """Проверка подписи Telegram Mini App. Возвращает user id или None."""
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        got = data.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        want = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, got):
            return None
        if time.time() - int(data.get("auth_date", 0)) > MAX_AGE:
            return None
        return int(json.loads(data["user"])["id"])
    except Exception:
        return None


class Panel:
    def __init__(self, sniper, cfg):
        self.s = sniper
        self.cfg = cfg
        self.token = cfg["panel"]["token"]
        self.url = f"https://{cfg['panel']['domain']}/"
        self.bot = None
        self.models = []           # последний список моделей подарков

    # ---------- данные для мини-аппа ----------

    def state(self):
        s, cfg = self.s, self.cfg
        now = time.monotonic()
        gifts = cfg["gifts"]
        return {
            "enabled": cfg["enabled"],
            "phase": s.phase,
            "issued": s.issued,
            "targets": core.short_targets(cfg["targets"], limit=40),
            "next_target": s.next_target(s.issued) if s.issued is not None else None,
            "early": cfg["early"],
            "rate": cfg["rate"],
            "idle_poll": cfg["idle_poll"],
            "slug": s.collection_slug(),
            "slug_base": cfg.get("slug") or "",
            "selected": {"count": len(gifts),
                         "gift_id": gifts[0]["gift_id"] if gifts else None,
                         "accounts": sorted({g["account"] for g in gifts})},
            "accounts": [{"name": a.name, "requests": a.requests, "floods": a.floods,
                          "cooldown": max(0, round(a.cooldown_until - now))}
                         for a in s.accounts.values()],
            "models": self.models,
        }

    async def load_models(self):
        """Подарки со всех аккаунтов, сгруппированные по модели."""
        s = self.s
        gifts = []
        for acc in s.accounts.values():
            gifts += [s.describe(sg, acc.name) for sg in await s.saved_gifts(acc)]
        s.gift_list = gifts
        models = {}
        for d in gifts:
            m = models.setdefault(d["gift_id"], {
                "gift_id": str(d["gift_id"]), "label": d["label"], "count": 0,
                "by_account": {}, "can_upgrade": 0, "prepaid": 0, "numbered": 0})
            m["count"] += 1
            m["by_account"][d["account"]] = m["by_account"].get(d["account"], 0) + 1
            m["can_upgrade"] += d["can_upgrade"]
            m["prepaid"] += d["prepaid"]
            m["numbered"] += bool(d["gift_num"])
        self.models = sorted(models.values(), key=lambda m: -m["count"])

    def select(self, gift_id, limit=None):
        picked = [d for d in self.s.gift_list if str(d["gift_id"]) == str(gift_id)]
        if not picked:
            raise ValueError("подарок не найден — обновите список")
        if limit:
            picked = picked[:max(1, int(limit))]
        self.cfg["gifts"] = [{k: d[k] for k in ("account", "msg_id", "saved_id",
                                                "gift_id", "title")} for d in picked]
        core.save_config(self.cfg)

    def apply_settings(self, body):
        cfg = self.cfg
        if "targets" in body:
            nums = core.parse_targets(str(body["targets"]))
            if not nums:
                raise ValueError("укажите хотя бы один номер")
            cfg["targets"] = nums
        if "early" in body:
            cfg["early"] = max(0, int(body["early"]))
        if "rate" in body:
            cfg["rate"] = min(1000.0, max(0.1, float(body["rate"])))
        if "idle_poll" in body:
            cfg["idle_poll"] = max(5.0, float(body["idle_poll"]))
        if "slug" in body:
            cfg["slug"] = core.slug_base(str(body["slug"])) or None
        core.save_config(cfg)

    # ---------- HTTP ----------

    def auth(self, request):
        raw = request.headers.get("X-Init-Data", "")
        if not raw:
            raise web.HTTPForbidden(text="Telegram не передал данные входа — "
                                         "откройте панель кнопкой «Панель» в боте.")
        uid = check_init_data(raw, self.token)
        if uid is None:
            raise web.HTTPForbidden(text="подпись Telegram не прошла проверку "
                                         "(панель открыта не из этого бота?)")
        if uid not in self.s.owner_ids:
            raise web.HTTPForbidden(text=f"аккаунт id {uid} не подключён к боту. "
                                         "Откройте панель с Hateless или Alex.")

    async def handle(self, request):
        self.auth(request)
        action = request.match_info["action"]
        body = await request.json() if request.can_read_body else {}
        s, cfg = self.s, self.cfg
        text = None
        try:
            if action == "state":
                pass
            elif action == "gifts":
                await self.load_models()
            elif action == "select":
                self.select(body["gift_id"], body.get("limit"))
            elif action == "settings":
                self.apply_settings(body)
            elif action == "hunt":
                if body.get("on"):
                    if not cfg["gifts"]:
                        raise ValueError("сначала выберите подарки")
                    cfg["enabled"] = True
                    core.save_config(cfg)
                    s.phase, s.last_note = "idle", ""
                else:
                    s.finish("idle")
            elif action == "test":
                text = await s.cmd_test()
            elif action == "ping":
                text = await s.cmd_ping()
            elif action == "now":
                text = await s.cmd_now()
            else:
                raise web.HTTPNotFound()
        except (ValueError, KeyError) as e:
            return web.json_response({"error": str(e), "state": self.state()})
        return web.json_response({"ok": True, "text": text, "state": self.state()})

    async def index(self, request):
        return web.FileResponse(HERE / "panel.html",
                                headers={"Cache-Control": "no-store"})

    # ---------- бот ----------

    async def start_bot(self):
        cfg = self.cfg
        self.bot = TelegramClient(str(core.DATA / "panelbot"), cfg["api_id"],
                                  cfg["api_hash"])
        await self.bot.start(bot_token=self.token)
        await self.bot(functions.bots.SetBotMenuButtonRequest(
            user_id=types.InputUserEmpty(),
            button=types.BotMenuButton(text="Панель", url=self.url)))

        @self.bot.on(events.NewMessage(incoming=True))
        async def _(event):
            if event.sender_id not in self.s.owner_ids:
                return
            await event.reply("Нажмите кнопку «Панель» слева от поля ввода. "
                              "Сюда будут приходить уведомления бота.")

        async def notify(text):
            for uid in self.s.owner_ids:
                if uid == self.s.main_id:
                    await self.bot.send_message(uid, text)
        self.s.notifier = notify

    async def start(self):
        await self.start_bot()
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_post("/api/{action}", self.handle)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", PORT).start()
        return self.bot
