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

# Тексты профиля бота: ставятся при каждом запуске (менять здесь)
BOT_DESCRIPTION = """🎯 Numbe Help — помощник для улучшения подарков Telegram.

🎁 Следит за выходом улучшений
🔢 Ловит нужные номера: 777, 1000 и другие
⚡ Ускоряется у самой цели
🔔 Присылает уведомления о результате

Нажмите «Панель» внизу, чтобы открыть настройки.
🔒 Работает только для владельца."""
BOT_ABOUT = "🎯 Ловлю красивые номера при улучшении подарков. Управление — кнопка «Панель»."


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
            "plan": [dict(e, status=s.done.get(e["t"])) for e in cfg["plan"][:300]],
            "plan_size": len(cfg["plan"]),
            "plan_need": sum(e["n"] for e in cfg["plan"]),
            "pool": len(s.pool) if s.phase == "hot" else None,
            "next_target": s.next_target(s.issued) if s.issued is not None else None,
            "early": cfg["early"],
            "early_auto": cfg.get("early_auto", True), "early_now": s.early_now(),
            "speed": round(s.speed(), 1), "rtt_ms": round(s.rtt() * 1000, 1) if s.rtts else None,
            "rate": cfg["rate"],
            "idle_poll": cfg["idle_poll"],
            "boost": cfg["boost"], "boost_window": cfg["boost_window"],
            "boost_rate": cfg["boost_rate"], "boosting": s.boosting(),
            "rate_now": s.effective_rate(),
            "slug": s.collection_slug(),
            "slug_base": cfg.get("slug") or "",
            "selected": {"count": len(gifts),
                         "gift_id": str(gifts[0]["gift_id"]) if gifts else None,
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
        if "plan" in body:
            plan = core.clean_plan(body["plan"])
            if not plan:
                raise ValueError("добавьте хотя бы один номер")
            cfg["plan"] = plan
        if "early" in body:
            cfg["early"] = max(0, int(body["early"]))
        if "early_auto" in body:
            cfg["early_auto"] = bool(body["early_auto"])
        if "rate" in body:
            cfg["rate"] = min(1000.0, max(0.1, float(body["rate"])))
        if "idle_poll" in body:
            cfg["idle_poll"] = max(5.0, float(body["idle_poll"]))
        if "boost" in body:
            cfg["boost"] = bool(body["boost"])
        if "boost_window" in body:
            cfg["boost_window"] = max(1, min(1000, int(body["boost_window"])))
        if "boost_rate" in body:
            cfg["boost_rate"] = min(1000.0, max(0.5, float(body["boost_rate"])))
        if "slug" in body:
            cfg["slug"] = core.slug_base(str(body["slug"])) or None
        core.save_config(cfg)

    # ---------- HTTP ----------

    def auth(self, request):
        """Пускаем только наши аккаунты. Чужим — без подробностей (причина — в журнал)."""
        raw = request.headers.get("X-Init-Data", "")
        uid = check_init_data(raw, self.token) if raw else None
        if uid is None or uid not in self.s.owner_ids:
            why = ("нет данных входа" if not raw else
                   "неверная подпись" if uid is None else f"чужой аккаунт id {uid}")
            print(f"Панель: отказ в доступе ({why})")
            raise web.HTTPForbidden(text="locked")

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
        try:
            await self.bot(functions.bots.SetBotInfoRequest(
                lang_code="", about=BOT_ABOUT, description=BOT_DESCRIPTION))
        except Exception as e:      # тексты не важнее запуска панели
            print("Не удалось обновить описание бота:", e)

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
        app.router.add_static("/sounds/", HERE / "sounds")   # озвучка подсказок
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", PORT).start()
        return self.bot
