"""Gift Sniper: улучшает выбранный подарок Telegram в нужный момент.

Работает как юзербот (Telethon) от имени аккаунта владельца.
Управление: команды в «Избранном» (Saved Messages), список — /help.
Данные (сессия, настройки) лежат в ~/.giftsniper/ и никуда не отправляются.
"""

import asyncio
import json
import re
import statistics
import time
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError
from telethon.tl import functions, types

DATA = Path.home() / ".giftsniper"
CONFIG = DATA / "config.json"
SESSION = str(DATA / "session")

DEFAULTS = {
    "enabled": False,       # охота включена
    "gift": None,           # выбранный подарок: msg_id / saved_id / gift_id / title
    "targets": [777],       # номера, которые ловим (по возрастанию)
    "early": 3,             # за сколько номеров до цели отправлять запрос
    "slug": None,           # основа ссылки коллекции, напр. "PlushPepe"
    "idle_poll": 30.0,      # секунд между проверками, пока улучшений нет
    "hot_poll": 0.35,       # секунд между проверками счётчика во время охоты
    "keep_details": False,  # сохранять подпись отправителя на коллекционке
}

HELP = """🎯 Gift Sniper — команды (пишите здесь, в Избранном):

/status — что бот делает сейчас
/gifts — ваши подарки, которые можно улучшить
/gift 2 — выбрать подарок №2 из списка /gifts
/target 777 — какой номер ловить (можно несколько: /target 777 1000)
/early 3 — за сколько номеров до цели стрелять
/on — включить охоту, /off — выключить
/ping — замерить скорость связи с Telegram
/test — пробный прогон без улучшения
/slug PlushPepe — задать ссылку коллекции вручную (обычно не нужно)
/now — улучшить выбранный подарок прямо сейчас
/help — эта справка"""


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG.exists():
        cfg.update(json.loads(CONFIG.read_text()))
    return cfg


def save_config(cfg):
    DATA.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def slug_base(title):
    """«Plush Pepe» → «PlushPepe»: так Telegram строит ссылки t.me/nft/…"""
    return re.sub(r"[^0-9A-Za-z]", "", title or "")


class Sniper:
    def __init__(self, client, cfg):
        self.client = client
        self.cfg = cfg
        self.gift_list = []       # результат последнего /gifts
        self.phase = "idle"       # idle / wait / hot / done
        self.issued = None        # сколько уже улучшено (счётчик коллекции)
        self.last_note = ""
        self.form = None          # заранее полученная форма оплаты
        self.form_time = 0.0
        self.busy = False

    # ---------- общение ----------

    async def say(self, text):
        await self.client.send_message("me", text)

    async def note_once(self, text):
        """Не повторять одно и то же сообщение в цикле."""
        if text != self.last_note:
            self.last_note = text
            await self.say(text)

    # ---------- подарки ----------

    async def saved_gifts(self):
        result, offset = [], ""
        while True:
            r = await self.client(functions.payments.GetSavedStarGiftsRequest(
                peer=types.InputPeerSelf(), offset=offset, limit=100,
                exclude_unique=True))
            result += r.gifts
            if not r.next_offset:
                return result
            offset = r.next_offset

    def gift_ref(self, g=None):
        g = g or self.cfg["gift"]
        if g.get("msg_id"):
            return types.InputSavedStarGiftUser(msg_id=g["msg_id"])
        return types.InputSavedStarGiftChat(peer=types.InputPeerSelf(),
                                            saved_id=g["saved_id"])

    @staticmethod
    def describe(sg):
        gift = sg.gift
        return {
            "msg_id": sg.msg_id,
            "saved_id": sg.saved_id,
            "gift_id": gift.id,
            "title": getattr(gift, "title", None) or f"Подарок {gift.id}",
            "gift_num": sg.gift_num,
            "can_upgrade": bool(sg.can_upgrade),
            "prepaid": bool(sg.upgrade_stars),
            "price": getattr(gift, "upgrade_stars", None),
        }

    async def current(self):
        """Свежие данные о выбранном подарке (или None, если его уже нет)."""
        want = self.cfg["gift"]
        for sg in await self.saved_gifts():
            d = self.describe(sg)
            if (want.get("msg_id") and d["msg_id"] == want["msg_id"]) or \
               (want.get("saved_id") and d["saved_id"] == want["saved_id"]):
                return d
        return None

    async def counter(self):
        """Сколько подарков этой модели уже улучшено (по коллекционке №1)."""
        base = self.cfg.get("slug") or slug_base(self.cfg["gift"]["title"])
        r = await self.client(functions.payments.GetUniqueStarGiftRequest(
            slug=f"{base}-1"))
        return r.gift.availability_issued

    # ---------- улучшение ----------

    async def prepare_form(self, info):
        if info["prepaid"]:
            self.form = None
            return
        if self.form and time.monotonic() - self.form_time < 60:
            return
        invoice = types.InputInvoiceStarGiftUpgrade(
            stargift=self.gift_ref(), keep_original_details=self.cfg["keep_details"])
        self.form = (await self.client(functions.payments.GetPaymentFormRequest(
            invoice=invoice)), invoice)
        self.form_time = time.monotonic()

    async def fire(self, info):
        t0 = time.monotonic()
        if info["prepaid"]:
            res = await self.client(functions.payments.UpgradeStarGiftRequest(
                stargift=self.gift_ref(),
                keep_original_details=self.cfg["keep_details"]))
        else:
            await self.prepare_form(info)
            form, invoice = self.form
            res = await self.client(functions.payments.SendStarsFormRequest(
                form_id=form.form_id, invoice=invoice))
        ms = (time.monotonic() - t0) * 1000
        num = self.find_num(res)
        return num, ms

    @staticmethod
    def find_num(res):
        """Ищет номер новой коллекционки в ответе Telegram."""
        if isinstance(res, types.payments.PaymentResult):
            res = res.updates               # оплата звёздами: Updates внутри
        if hasattr(res, "updates"):        # Updates / UpdatesCombined
            updates = res.updates
        elif hasattr(res, "update"):       # UpdateShort
            updates = [res.update]
        else:
            updates = []
        for u in updates or []:
            msg = getattr(u, "message", None)
            action = getattr(msg, "action", None)
            if isinstance(action, types.MessageActionStarGiftUnique):
                return getattr(action.gift, "num", None)
        return None

    # ---------- главный цикл ----------

    def next_target(self, issued):
        """Ближайший номер, который ещё можно поймать."""
        for t in sorted(self.cfg["targets"]):
            if t > issued:
                return t
        return None

    async def loop(self):
        while True:
            try:
                await self.step()
            except FloodWaitError as e:
                await self.say(f"⏳ Telegram просит подождать {e.seconds} с "
                               "(слишком частые запросы). Жду.")
                await asyncio.sleep(e.seconds + 1)
            except RPCError as e:
                await self.note_once(f"⚠️ Ошибка Telegram: {e}")
                await asyncio.sleep(5)
            except Exception as e:  # бот не должен падать
                await self.note_once(f"⚠️ Ошибка: {e!r}")
                await asyncio.sleep(5)

    async def step(self):
        cfg = self.cfg
        if not cfg["enabled"] or not cfg["gift"] or self.busy:
            self.phase = "idle"
            await asyncio.sleep(2)
            return

        if self.phase in ("idle", "wait"):
            info = await self.current()
            if info is None:
                cfg["enabled"] = False
                save_config(cfg)
                await self.say("❌ Выбранный подарок не найден (продан, передан "
                               "или уже улучшен). Охота выключена.")
                return
            if info["gift_num"]:
                cfg["enabled"] = False
                save_config(cfg)
                await self.say(
                    f"ℹ️ У подарка «{info['title']}» номер уже назначен "
                    f"Telegram: #{info['gift_num']}. От скорости улучшения он "
                    "не зависит, поэтому охота выключена. Улучшить можно "
                    "командой /now, когда улучшения откроются.")
                return
            if not info["can_upgrade"]:
                self.phase = "wait"
                await self.note_once(f"🕐 Жду выхода улучшений для "
                                     f"«{info['title']}». Проверяю раз в "
                                     f"{cfg['idle_poll']:.0f} с.")
                await asyncio.sleep(cfg["idle_poll"])
                return
            self.phase = "hot"
            self.info = info
            await self.say(f"🔥 Улучшения для «{info['title']}» доступны! "
                           f"Цели: {cfg['targets']}, стреляю за "
                           f"{cfg['early']} номер(а) до цели.")

        # фаза hot: следим за счётчиком
        try:
            issued = await self.counter()
        except RPCError:
            await self.note_once("🔎 Коллекция ещё не появилась (никто не "
                                 "улучшил первым) или ссылка не та. Жду… "
                                 "Если долго так — задайте /slug.")
            await asyncio.sleep(2)
            return
        self.issued = issued
        target = self.next_target(issued)
        if target is None:
            cfg["enabled"] = False
            save_config(cfg)
            self.phase = "done"
            await self.say(f"😔 Все цели уже прошли (улучшено {issued}). "
                           "Охота выключена. Задайте новые /target.")
            return

        gap = target - (issued + 1)   # сколько номеров до цели
        if gap <= cfg["early"] + 30:
            await self.prepare_form(self.info)   # оплату готовим заранее
        if gap <= cfg["early"]:
            num, ms = await self.fire(self.info)
            cfg["enabled"] = False
            save_config(cfg)
            self.phase = "done"
            if num is None:
                await self.say(f"✅ Подарок улучшен (запрос {ms:.0f} мс). "
                               "Номер не удалось прочитать — посмотрите в "
                               "профиле.")
            elif num == target or num in cfg["targets"]:
                await self.say(f"🎉 ПОЙМАЛ! Номер #{num} (запрос {ms:.0f} мс).")
            else:
                await self.say(f"Улучшено: номер #{num}, цель была #{target} "
                               f"(запрос {ms:.0f} мс). Можно подстроить /early.")
            return
        await asyncio.sleep(cfg["hot_poll"])

    # ---------- команды ----------

    async def on_command(self, event):
        text = event.raw_text.strip()
        cmd, _, arg = text.partition(" ")
        cmd = cmd.lower().split("@")[0]
        cfg = self.cfg
        try:
            if cmd in ("/help", "/start"):
                await self.say(HELP)
            elif cmd == "/status":
                await self.say(self.status_text())
            elif cmd == "/gifts":
                await self.cmd_gifts()
            elif cmd == "/gift":
                await self.cmd_gift(arg)
            elif cmd == "/target":
                nums = sorted({int(x) for x in re.findall(r"\d+", arg)})
                if not nums:
                    raise ValueError("укажите номер, например /target 777")
                cfg["targets"] = nums
                save_config(cfg)
                await self.say(f"🎯 Цели: {nums}")
            elif cmd == "/early":
                cfg["early"] = max(0, int(arg))
                save_config(cfg)
                await self.say(f"⏱ Стреляю за {cfg['early']} номер(а) до цели.")
            elif cmd == "/slug":
                cfg["slug"] = slug_base(arg) or None
                save_config(cfg)
                await self.say(f"🔗 Коллекция: {cfg['slug'] or 'по названию'}")
            elif cmd == "/on":
                if not cfg["gift"]:
                    raise ValueError("сначала выберите подарок: /gifts, потом /gift N")
                cfg["enabled"] = True
                save_config(cfg)
                self.last_note = ""
                await self.say("✅ Охота включена. /status — что происходит.")
            elif cmd == "/off":
                cfg["enabled"] = False
                save_config(cfg)
                await self.say("⏹ Охота выключена.")
            elif cmd == "/ping":
                await self.cmd_ping()
            elif cmd == "/test":
                await self.cmd_test()
            elif cmd == "/now":
                await self.cmd_now()
        except Exception as e:
            await self.say(f"⚠️ {e}")

    def status_text(self):
        cfg = self.cfg
        g = cfg["gift"]
        lines = [
            f"Охота: {'включена ✅' if cfg['enabled'] else 'выключена ⏹'}",
            f"Подарок: {g['title'] if g else 'не выбран (/gifts)'}",
            f"Цели: {cfg['targets']}, стреляю за {cfg['early']}",
            f"Этап: {self.phase}",
        ]
        if self.issued is not None:
            lines.append(f"Улучшено в коллекции: {self.issued}")
        return "\n".join(lines)

    async def cmd_gifts(self):
        gifts = [self.describe(sg) for sg in await self.saved_gifts()]
        self.gift_list = gifts
        if not gifts:
            await self.say("Подарков, которые можно улучшить, не найдено.")
            return
        lines = ["Ваши подарки (выбор: /gift N):"]
        for i, d in enumerate(gifts, 1):
            extra = []
            if d["gift_num"]:
                extra.append(f"номер уже #{d['gift_num']}")
            extra.append("улучшение доступно" if d["can_upgrade"]
                         else "улучшений пока нет")
            if d["prepaid"]:
                extra.append("улучшение оплачено")
            lines.append(f"{i}. {d['title']} — " + ", ".join(extra))
        await self.say("\n".join(lines))

    async def cmd_gift(self, arg):
        if not self.gift_list:
            raise ValueError("сначала отправьте /gifts")
        i = int(arg) - 1
        if not 0 <= i < len(self.gift_list):
            raise ValueError("нет подарка с таким номером в списке")
        d = self.gift_list[i]
        self.cfg["gift"] = {k: d[k] for k in ("msg_id", "saved_id", "gift_id",
                                               "title")}
        save_config(self.cfg)
        note = ""
        if d["gift_num"]:
            note = (f"\nℹ️ Номер этого подарка уже назначен: #{d['gift_num']}. "
                    "Скорость улучшения его не изменит.")
        await self.say(f"🎁 Выбран: {d['title']}{note}")

    async def cmd_ping(self):
        samples = []
        for _ in range(7):
            t0 = time.monotonic()
            await self.client(functions.help.GetNearestDcRequest())
            samples.append((time.monotonic() - t0) * 1000)
        dc = self.client.session.dc_id
        await self.say(f"📶 Отклик Telegram (DC{dc}): мин {min(samples):.1f} мс, "
                       f"медиана {statistics.median(samples):.1f} мс.")

    async def cmd_test(self):
        if not self.cfg["gift"]:
            raise ValueError("сначала выберите подарок: /gifts, потом /gift N")
        info = await self.current()
        if info is None:
            raise ValueError("выбранный подарок не найден")
        lines = [f"🧪 Пробный прогон для «{info['title']}» (без улучшения):",
                 f"• улучшение доступно: {'да' if info['can_upgrade'] else 'нет'}",
                 f"• улучшение оплачено заранее: {'да' if info['prepaid'] else 'нет'}"]
        if info["gift_num"]:
            lines.append(f"• номер уже назначен: #{info['gift_num']}")
        try:
            issued = await self.counter()
            lines.append(f"• уже улучшено в коллекции: {issued}")
        except RPCError as e:
            lines.append(f"• счётчик коллекции недоступен ({e.__class__.__name__}),"
                         " коллекции ещё нет или нужен /slug")
        if info["can_upgrade"] and not info["prepaid"]:
            try:
                t0 = time.monotonic()
                await self.prepare_form(info)
                ms = (time.monotonic() - t0) * 1000
                price = self.form[0].invoice.prices[0].amount
                lines.append(f"• форма оплаты готова за {ms:.0f} мс, цена {price} ⭐")
            except Exception as e:
                lines.append(f"• форма оплаты: ошибка {e}")
        await self.say("\n".join(lines))

    async def cmd_now(self):
        if not self.cfg["gift"]:
            raise ValueError("сначала выберите подарок: /gifts, потом /gift N")
        info = await self.current()
        if info is None or not info["can_upgrade"]:
            raise ValueError("улучшение этого подарка сейчас недоступно")
        self.busy = True
        try:
            num, ms = await self.fire(info)
        finally:
            self.busy = False
        self.cfg["enabled"] = False
        save_config(self.cfg)
        await self.say(f"✅ Улучшено{f': номер #{num}' if num else ''} "
                       f"(запрос {ms:.0f} мс).")


async def main():
    cfg = load_config()
    if not cfg.get("api_id"):
        raise SystemExit("Сначала выполните вход: giftsniper-login")
    client = TelegramClient(SESSION, cfg["api_id"], cfg["api_hash"],
                            device_model="Gift Sniper", system_version="server")
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Сессия не авторизована: выполните giftsniper-login")
    sniper = Sniper(client, cfg)

    @client.on(events.NewMessage(chats="me", pattern=r"^/"))
    async def _(event):
        await sniper.on_command(event)

    await sniper.say("🤖 Gift Sniper запущен. /help — команды.\n\n"
                     + sniper.status_text())
    await asyncio.gather(client.run_until_disconnected(), sniper.loop())


if __name__ == "__main__":
    asyncio.run(main())
