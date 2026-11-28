"""Gift Sniper: улучшает подарки Telegram, когда счётчик коллекции подходит к цели.

Юзербот (Telethon), может работать с несколькими аккаунтами сразу:
- все аккаунты по очереди опрашивают счётчик коллекции (общая частота — /rate);
- выбранные подарки со всех аккаунтов улучшаются одним залпом.
Управление — командами в «Избранном» главного аккаунта (/help).
Данные (сессии, настройки) лежат в ~/.giftsniper/ и никуда не отправляются.
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
ACCOUNTS = DATA / "accounts"
CONFIG = DATA / "config.json"
MAIN = "main"

DEFAULTS = {
    "enabled": False,       # охота включена
    "gifts": [],            # выбранные подарки: account / msg_id / saved_id / gift_id / title
    "targets": [777],       # номера, которые ловим
    "early": 3,             # за сколько номеров до цели стрелять
    "rate": 5.0,            # запросов счётчика в секунду (всего, на все аккаунты)
    "idle_poll": 30.0,      # секунд между проверками, пока улучшений нет
    "slug": None,           # основа ссылки коллекции, напр. "PlushPepe"
    "keep_details": False,  # сохранять подпись отправителя на коллекционке
}
MAX_TARGETS = 10000

HELP = """🎯 Gift Sniper — команды (пишите здесь, в Избранном):

/status — что бот делает сейчас
/accounts — подключённые аккаунты
/gifts — подарки на всех аккаунтах, которые можно улучшить
/gift 1 3 — выбрать подарки №1 и №3 (залп), /gift all — все одной модели
/target 777 — какие номера ловить: /target 777 1000 1111-1115
/early 3 — за сколько номеров до цели стрелять
/rate 5 — запросов счётчика в секунду (всего на все аккаунты)
/idle 30 — раз во сколько секунд проверять, вышли ли улучшения
/on — включить охоту, /off — выключить
/ping — скорость связи с Telegram у каждого аккаунта
/test — пробный прогон без улучшения
/now — улучшить выбранные подарки прямо сейчас
/slug PlushPepe — ссылка коллекции вручную (обычно не нужно)
/help — эта справка

Добавить аккаунт: на сервере команда giftsniper-login имя"""


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG.exists():
        cfg.update(json.loads(CONFIG.read_text()))
    if cfg.get("gift") and not cfg["gifts"]:      # формат первой версии
        cfg["gifts"] = [dict(cfg["gift"], account=MAIN)]
    cfg.pop("gift", None)
    return cfg


def save_config(cfg):
    DATA.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    CONFIG.chmod(0o600)


def migrate_old_session():
    """Первая версия хранила одну сессию в ~/.giftsniper/session.session."""
    old = DATA / "session.session"
    new = ACCOUNTS / f"{MAIN}.session"
    if old.exists() and not new.exists():
        ACCOUNTS.mkdir(parents=True, exist_ok=True)
        old.rename(new)


def account_names():
    names = sorted(p.stem for p in ACCOUNTS.glob("*.session"))
    if MAIN in names:                          # главный — первым
        names.remove(MAIN)
        names.insert(0, MAIN)
    return names


def make_client(name, cfg):
    return TelegramClient(str(ACCOUNTS / name), cfg["api_id"], cfg["api_hash"],
                          device_model="Gift Sniper", system_version="server")


def slug_base(title):
    """«Plush Pepe» → «PlushPepe»: так Telegram строит ссылки t.me/nft/…"""
    return re.sub(r"[^0-9A-Za-z]", "", title or "")


def parse_targets(text):
    """«777 1000 1111-1115» → [777, 1000, 1111, …, 1115]."""
    nums = set()
    for a, b, single in re.findall(r"(\d+)\s*-\s*(\d+)|(\d+)", text):
        if single:
            nums.add(int(single))
        else:
            lo, hi = sorted((int(a), int(b)))
            nums.update(range(lo, hi + 1))
        if len(nums) > MAX_TARGETS:
            raise ValueError(f"слишком много номеров (больше {MAX_TARGETS})")
    nums.discard(0)
    return sorted(nums)


def short_targets(nums, limit=12):
    """Короткая запись списка целей: 777, 1000, 1111–1115."""
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(str(nums[i]) if i == j else f"{nums[i]}–{nums[j]}")
        i = j + 1
    text = ", ".join(parts[:limit])
    return text + (f" … (+{len(parts) - limit})" if len(parts) > limit else "")


class Account:
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.cooldown_until = 0.0    # после FloodWait аккаунт отдыхает
        self.requests = 0
        self.floods = 0


class Sniper:
    def __init__(self, accounts, cfg):
        self.accounts = accounts          # {имя: Account}, главный первым
        self.main = next(iter(accounts.values()))
        self.cfg = cfg
        self.gift_list = []               # результат последнего /gifts
        self.phase = "idle"               # idle / wait / hot / done
        self.issued = None                # сколько уже улучшено в коллекции
        self.counter_error = None
        self.shots = []                   # подарки, готовые к улучшению
        self.forms = {}                   # заранее полученные формы оплаты
        self.pollers = []
        self.last_note = ""
        self.busy = False

    # ---------- общение ----------

    async def say(self, text):
        await self.main.client.send_message("me", text)

    async def note_once(self, text):
        if text != self.last_note:
            self.last_note = text
            await self.say(text)

    # ---------- подарки ----------

    async def saved_gifts(self, acc):
        result, offset = [], ""
        while True:
            r = await acc.client(functions.payments.GetSavedStarGiftsRequest(
                peer=types.InputPeerSelf(), offset=offset, limit=100,
                exclude_unique=True))
            result += r.gifts
            if not r.next_offset:
                return result
            offset = r.next_offset

    @staticmethod
    def describe(sg, account):
        gift = sg.gift
        return {
            "account": account,
            "msg_id": sg.msg_id,
            "saved_id": sg.saved_id,
            "gift_id": gift.id,
            "title": getattr(gift, "title", None) or f"Подарок {gift.id}",
            "gift_num": sg.gift_num,
            "can_upgrade": bool(sg.can_upgrade),
            "prepaid": bool(sg.upgrade_stars),
        }

    @staticmethod
    def key(g):
        return (g["account"], g.get("msg_id"), g.get("saved_id"))

    @staticmethod
    def gift_ref(g):
        if g.get("msg_id"):
            return types.InputSavedStarGiftUser(msg_id=g["msg_id"])
        return types.InputSavedStarGiftChat(peer=types.InputPeerSelf(),
                                            saved_id=g["saved_id"])

    async def fresh(self):
        """Свежие данные о выбранных подарках: [(выбор, info или None)]."""
        out = []
        cache = {}
        for g in self.cfg["gifts"]:
            acc = self.accounts.get(g["account"])
            if acc is None:
                out.append((g, None))
                continue
            if acc.name not in cache:
                cache[acc.name] = [self.describe(sg, acc.name)
                                   for sg in await self.saved_gifts(acc)]
            info = next((d for d in cache[acc.name]
                         if self.key(d) == self.key(g)), None)
            out.append((g, info))
        return out

    # ---------- счётчик коллекции ----------

    def collection_slug(self):
        title = self.cfg["gifts"][0]["title"] if self.cfg["gifts"] else ""
        return f"{self.cfg.get('slug') or slug_base(title)}-1"

    async def read_counter(self, acc):
        acc.requests += 1
        r = await acc.client(functions.payments.GetUniqueStarGiftRequest(
            slug=self.collection_slug()))
        return r.gift.availability_issued

    async def poller(self, acc, offset):
        """Каждый аккаунт опрашивает счётчик в своё окно, вместе — /rate в секунду."""
        await asyncio.sleep(offset)
        while self.phase == "hot":
            interval = len(self.accounts) / max(self.cfg["rate"], 0.01)
            now = time.monotonic()
            if now < acc.cooldown_until:
                await asyncio.sleep(min(acc.cooldown_until - now, 5))
                continue
            try:
                value = await self.read_counter(acc)
                self.issued = max(self.issued or 0, value)
                self.counter_error = None
            except FloodWaitError as e:
                acc.floods += 1
                acc.cooldown_until = time.monotonic() + e.seconds + 1
                await self.say(f"⏳ [{acc.name}] Telegram просит паузу {e.seconds} с "
                               "— этот аккаунт отдыхает, остальные работают. "
                               "Если такое часто — уменьшите /rate.")
            except RPCError as e:
                self.counter_error = e
            await asyncio.sleep(interval)

    def start_pollers(self):
        self.stop_pollers()
        n = len(self.accounts)
        step = n / max(self.cfg["rate"], 0.01) / n
        self.pollers = [asyncio.create_task(self.poller(acc, i * step))
                        for i, acc in enumerate(self.accounts.values())]

    def stop_pollers(self):
        for t in self.pollers:
            t.cancel()
        self.pollers = []

    # ---------- улучшение ----------

    async def prepare_form(self, info):
        if info["prepaid"]:
            return
        k = self.key(info)
        if k in self.forms and time.monotonic() - self.forms[k][2] < 60:
            return
        acc = self.accounts[info["account"]]
        invoice = types.InputInvoiceStarGiftUpgrade(
            stargift=self.gift_ref(info),
            keep_original_details=self.cfg["keep_details"])
        form = await acc.client(functions.payments.GetPaymentFormRequest(
            invoice=invoice))
        self.forms[k] = (form, invoice, time.monotonic())

    async def prepare_all(self):
        await asyncio.gather(*(self.prepare_form(i) for i in self.shots),
                             return_exceptions=True)

    async def fire_one(self, info):
        acc = self.accounts[info["account"]]
        t0 = time.monotonic()
        try:
            if info["prepaid"]:
                res = await acc.client(functions.payments.UpgradeStarGiftRequest(
                    stargift=self.gift_ref(info),
                    keep_original_details=self.cfg["keep_details"]))
            else:
                await self.prepare_form(info)
                form, invoice, _ = self.forms[self.key(info)]
                res = await acc.client(functions.payments.SendStarsFormRequest(
                    form_id=form.form_id, invoice=invoice))
            return info, self.find_num(res), (time.monotonic() - t0) * 1000, None
        except Exception as e:
            return info, None, (time.monotonic() - t0) * 1000, e

    async def fire_all(self):
        """Залп: все готовые подарки улучшаются одновременно."""
        return await asyncio.gather(*(self.fire_one(i) for i in self.shots))

    @staticmethod
    def find_num(res):
        """Ищет номер новой коллекционки в ответе Telegram."""
        if isinstance(res, types.payments.PaymentResult):
            res = res.updates
        if hasattr(res, "updates"):
            updates = res.updates
        elif hasattr(res, "update"):
            updates = [res.update]
        else:
            updates = []
        for u in updates or []:
            action = getattr(getattr(u, "message", None), "action", None)
            if isinstance(action, types.MessageActionStarGiftUnique):
                return getattr(action.gift, "num", None)
        return None

    def report(self, results, target=None):
        lines, hit = [], False
        for info, num, ms, err in results:
            who = f"[{info['account']}] {info['title']}"
            if err:
                lines.append(f"❌ {who}: ошибка {err} ({ms:.0f} мс)")
            elif num is None:
                lines.append(f"✅ {who}: улучшен за {ms:.0f} мс, номер смотрите в профиле")
            else:
                mark = "🎉" if num in self.cfg["targets"] else "•"
                hit |= num in self.cfg["targets"]
                lines.append(f"{mark} {who}: #{num} ({ms:.0f} мс)")
        head = ("🎉 ПОЙМАЛ!" if hit else
                f"Залп выполнен{f', цель была #{target}' if target else ''}:")
        return head + "\n" + "\n".join(lines)

    # ---------- главный цикл ----------

    def next_target(self, issued):
        for t in self.cfg["targets"]:
            if t > issued:
                return t
        return None

    def finish(self, phase="done"):
        self.cfg["enabled"] = False
        save_config(self.cfg)
        self.phase = phase
        self.stop_pollers()

    async def loop(self):
        while True:
            try:
                await self.step()
            except FloodWaitError as e:
                await self.say(f"⏳ Telegram просит подождать {e.seconds} с. Жду.")
                await asyncio.sleep(e.seconds + 1)
            except RPCError as e:
                await self.note_once(f"⚠️ Ошибка Telegram: {e}")
                await asyncio.sleep(5)
            except Exception as e:  # бот не должен падать
                await self.note_once(f"⚠️ Ошибка: {e!r}")
                await asyncio.sleep(5)

    async def step(self):
        cfg = self.cfg
        if not cfg["enabled"] or not cfg["gifts"] or self.busy:
            if self.phase == "hot":
                self.stop_pollers()
            self.phase = "idle"
            await asyncio.sleep(1)
            return

        if self.phase in ("idle", "wait", "done"):
            await self.check_upgrades()
            return

        # фаза hot: решения по счётчику, который обновляют опросчики
        if self.issued is None:
            if self.counter_error:
                await self.note_once(
                    "🔎 Коллекция ещё не появилась (никто не улучшил первым) "
                    f"или ссылка «{self.collection_slug()}» не та. Жду… "
                    "Если долго так — задайте /slug.")
            await asyncio.sleep(0.05)
            return
        target = self.next_target(self.issued)
        if target is None:
            self.finish()
            await self.say(f"😔 Все цели уже прошли (улучшено {self.issued}). "
                           "Охота выключена. Задайте новые /target.")
            return
        gap = target - (self.issued + 1)       # сколько номеров до цели
        if gap <= cfg["early"] + 30:
            await self.prepare_all()            # оплату готовим заранее
        if gap <= cfg["early"]:
            results = await self.fire_all()
            self.finish()
            await self.say(self.report(results, target))
            return
        await asyncio.sleep(min(0.5, max(0.002, 0.5 / max(cfg["rate"], 1))))

    async def check_upgrades(self):
        cfg = self.cfg
        ready, waiting, notes = [], [], []
        for g, info in await self.fresh():
            if info is None:
                notes.append(f"❌ [{g['account']}] {g['title']}: подарок не найден "
                             "(продан, передан или уже улучшен) — убран из охоты")
                cfg["gifts"].remove(g)
            elif info["gift_num"]:
                notes.append(f"ℹ️ [{g['account']}] {g['title']}: номер уже назначен "
                             f"Telegram — #{info['gift_num']}, от скорости не зависит. "
                             "Убран из охоты (улучшить можно через /now).")
                cfg["gifts"].remove(g)
            elif info["can_upgrade"]:
                ready.append(info)
            else:
                waiting.append(info)
        save_config(cfg)
        if notes:
            await self.say("\n".join(notes))
        if not cfg["gifts"]:
            self.finish("idle")
            await self.say("Охотиться не на что — охота выключена. /gifts, /gift N.")
            return
        if not ready:
            self.phase = "wait"
            await self.note_once(f"🕐 Жду выхода улучшений ({len(waiting)} подарк.). "
                                 f"Проверяю раз в {cfg['idle_poll']:.0f} с.")
            await asyncio.sleep(cfg["idle_poll"])
            return
        self.shots, self.issued, self.forms = ready, None, {}
        self.phase = "hot"
        self.start_pollers()
        await self.say(f"🔥 Улучшения доступны! Готово к залпу: {len(ready)} подарк. "
                       f"Цели: {short_targets(cfg['targets'])}. Стреляю за "
                       f"{cfg['early']} номер(а) до цели, счётчик — "
                       f"{cfg['rate']:g} запр/с на {len(self.accounts)} аккаунт(а).")

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
            elif cmd == "/accounts":
                await self.cmd_accounts()
            elif cmd == "/gifts":
                await self.cmd_gifts()
            elif cmd == "/gift":
                await self.cmd_gift(arg)
            elif cmd == "/target":
                nums = parse_targets(arg)
                if not nums:
                    raise ValueError("укажите номер: /target 777 или /target 1000-1010")
                cfg["targets"] = nums
                save_config(cfg)
                await self.say(f"🎯 Цели ({len(nums)}): {short_targets(nums)}")
            elif cmd == "/early":
                cfg["early"] = max(0, int(arg))
                save_config(cfg)
                await self.say(f"⏱ Стреляю за {cfg['early']} номер(а) до цели.")
            elif cmd == "/rate":
                cfg["rate"] = min(1000.0, max(0.1, float(arg.replace(",", "."))))
                save_config(cfg)
                per = cfg["rate"] / len(self.accounts)
                warn = ("\n⚠️ Больше ~10 запросов в секунду на аккаунт — высокий "
                        "риск паузы от Telegram (FloodWait)." if per > 10 else "")
                await self.say(f"📡 Счётчик: {cfg['rate']:g} запр/с всего, "
                               f"≈{per:.1f} на аккаунт.{warn}")
            elif cmd == "/idle":
                cfg["idle_poll"] = max(5.0, float(arg.replace(",", ".")))
                save_config(cfg)
                await self.say(f"🕐 Пока улучшений нет, проверяю раз в "
                               f"{cfg['idle_poll']:g} с.")
            elif cmd == "/slug":
                cfg["slug"] = slug_base(arg) or None
                save_config(cfg)
                await self.say(f"🔗 Коллекция: {self.collection_slug()}")
            elif cmd == "/on":
                if not cfg["gifts"]:
                    raise ValueError("сначала выберите подарки: /gifts, потом /gift N")
                cfg["enabled"] = True
                save_config(cfg)
                self.phase, self.last_note = "idle", ""
                await self.say("✅ Охота включена. /status — что происходит.")
            elif cmd == "/off":
                self.finish("idle")
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
        lines = [
            f"Охота: {'включена ✅' if cfg['enabled'] else 'выключена ⏹'} (этап: {self.phase})",
            f"Аккаунтов: {len(self.accounts)}",
            f"Подарков в залпе: {len(cfg['gifts'])}"
            + (f" — {cfg['gifts'][0]['title']}" if cfg["gifts"] else " (выберите: /gifts)"),
            f"Цели: {short_targets(cfg['targets'])}",
            f"Стреляю за {cfg['early']} до цели · счётчик {cfg['rate']:g} запр/с · "
            f"ожидание раз в {cfg['idle_poll']:g} с",
        ]
        if self.issued is not None:
            lines.append(f"Улучшено в коллекции: {self.issued}")
        return "\n".join(lines)

    async def cmd_accounts(self):
        lines = ["Аккаунты:"]
        for acc in self.accounts.values():
            me = await acc.client.get_me()
            cd = acc.cooldown_until - time.monotonic()
            extra = f", отдыхает ещё {cd:.0f} с" if cd > 0 else ""
            lines.append(f"• {acc.name}: {me.first_name} (@{me.username or '-'}), "
                         f"запросов {acc.requests}, пауз {acc.floods}{extra}")
        lines.append("\nДобавить: на сервере giftsniper-login имя")
        await self.say("\n".join(lines))

    async def cmd_gifts(self):
        gifts = []
        for acc in self.accounts.values():
            gifts += [self.describe(sg, acc.name) for sg in await self.saved_gifts(acc)]
        self.gift_list = gifts
        if not gifts:
            await self.say("Подарков, которые можно улучшить, не найдено.")
            return
        lines = ["Подарки (выбор: /gift 1 3 или /gift all 1):"]
        for i, d in enumerate(gifts, 1):
            extra = []
            if d["gift_num"]:
                extra.append(f"номер уже #{d['gift_num']}")
            extra.append("улучшение доступно" if d["can_upgrade"]
                         else "улучшений пока нет")
            if d["prepaid"]:
                extra.append("оплачено")
            lines.append(f"{i}. [{d['account']}] {d['title']} — " + ", ".join(extra))
        await self.say("\n".join(lines))

    async def cmd_gift(self, arg):
        if not self.gift_list:
            raise ValueError("сначала отправьте /gifts")
        if arg.strip().lower().startswith("all"):
            # /gift all 2 — все подарки той же модели, что №2
            n = re.findall(r"\d+", arg)
            base = self.gift_list[int(n[0]) - 1] if n else self.gift_list[0]
            picked = [d for d in self.gift_list if d["gift_id"] == base["gift_id"]]
        else:
            idx = [int(x) - 1 for x in re.findall(r"\d+", arg)]
            if not idx or any(not 0 <= i < len(self.gift_list) for i in idx):
                raise ValueError("укажите номера из списка /gifts, например /gift 1 3")
            picked = [self.gift_list[i] for i in dict.fromkeys(idx)]
        if len({d["gift_id"] for d in picked}) > 1:
            raise ValueError("в одном залпе — только подарки одной модели "
                             "(у них общий счётчик номеров)")
        self.cfg["gifts"] = [{k: d[k] for k in ("account", "msg_id", "saved_id",
                                                "gift_id", "title")} for d in picked]
        save_config(self.cfg)
        lines = [f"🎁 В залпе {len(picked)} подарк. «{picked[0]['title']}»:"]
        for d in picked:
            num = f" — номер уже #{d['gift_num']}, скорость не важна" if d["gift_num"] else ""
            lines.append(f"• [{d['account']}]{num}")
        await self.say("\n".join(lines))

    async def cmd_ping(self):
        lines = ["📶 Отклик Telegram:"]
        for acc in self.accounts.values():
            samples = []
            for _ in range(7):
                t0 = time.monotonic()
                await acc.client(functions.help.GetNearestDcRequest())
                samples.append((time.monotonic() - t0) * 1000)
            lines.append(f"• {acc.name} (DC{acc.client.session.dc_id}): мин "
                         f"{min(samples):.1f} мс, медиана {statistics.median(samples):.1f} мс")
        await self.say("\n".join(lines))

    async def cmd_test(self):
        if not self.cfg["gifts"]:
            raise ValueError("сначала выберите подарки: /gifts, потом /gift N")
        lines = ["🧪 Пробный прогон (без улучшения):"]
        for g, info in await self.fresh():
            if info is None:
                lines.append(f"• [{g['account']}] {g['title']}: не найден")
                continue
            line = (f"• [{info['account']}] {info['title']}: улучшение "
                    f"{'доступно' if info['can_upgrade'] else 'недоступно'}, "
                    f"{'оплачено заранее' if info['prepaid'] else 'оплата звёздами'}")
            if info["gift_num"]:
                line += f", номер уже #{info['gift_num']}"
            if info["can_upgrade"] and not info["prepaid"]:
                try:
                    t0 = time.monotonic()
                    await self.prepare_form(info)
                    form = self.forms[self.key(info)][0]
                    line += (f", форма оплаты за {(time.monotonic() - t0) * 1000:.0f} мс,"
                             f" цена {form.invoice.prices[0].amount} ⭐")
                except Exception as e:
                    line += f", форма оплаты: ошибка {e}"
            lines.append(line)
        try:
            t0 = time.monotonic()
            issued = await self.read_counter(self.main)
            lines.append(f"• счётчик «{self.collection_slug()}»: {issued} "
                         f"({(time.monotonic() - t0) * 1000:.0f} мс)")
        except RPCError as e:
            lines.append(f"• счётчик «{self.collection_slug()}» недоступен "
                         f"({e.__class__.__name__}): коллекции ещё нет или нужен /slug")
        await self.say("\n".join(lines))

    async def cmd_now(self):
        if not self.cfg["gifts"]:
            raise ValueError("сначала выберите подарки: /gifts, потом /gift N")
        ready = [i for _, i in await self.fresh() if i and i["can_upgrade"]]
        if not ready:
            raise ValueError("улучшение выбранных подарков сейчас недоступно")
        self.busy = True
        try:
            self.shots = ready
            results = await self.fire_all()
        finally:
            self.busy = False
        self.finish("idle")
        await self.say(self.report(results))


async def main():
    migrate_old_session()
    cfg = load_config()
    if not cfg.get("api_id") or not account_names():
        raise SystemExit("Сначала выполните вход: giftsniper-login")
    accounts = {}
    for name in account_names():
        client = make_client(name, cfg)
        await client.connect()
        if await client.is_user_authorized():
            accounts[name] = Account(name, client)
        else:
            print(f"Аккаунт {name}: сессия не авторизована, пропускаю")
    if not accounts:
        raise SystemExit("Нет авторизованных аккаунтов: выполните giftsniper-login")
    sniper = Sniper(accounts, cfg)

    @sniper.main.client.on(events.NewMessage(chats="me", pattern=r"^/"))
    async def _(event):
        await sniper.on_command(event)

    await sniper.say(f"🤖 Gift Sniper запущен, аккаунтов: {len(accounts)}. "
                     "/help — команды.\n\n" + sniper.status_text())
    await asyncio.gather(sniper.main.client.run_until_disconnected(), sniper.loop())


if __name__ == "__main__":
    asyncio.run(main())
