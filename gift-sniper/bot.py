"""Gift Sniper: улучшает подарки Telegram, когда счётчик коллекции подходит к цели.

Юзербот (Telethon), может работать с несколькими аккаунтами сразу:
- все аккаунты по очереди опрашивают счётчик коллекции (общая частота — /rate);
- выбранные подарки со всех аккаунтов улучшаются одним залпом.
Управление — командами в «Избранном» главного аккаунта (/help).
Данные (сессии, настройки) лежат в ~/.giftsniper/ и никуда не отправляются.
"""

import asyncio
import collections
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
    "plan": [{"t": 777, "n": 1}],  # номера и сколько подарков на каждый
    "early": 0,             # за сколько номеров до цели стрелять (если не авто)
    "early_auto": True,     # считать упреждение само: скорость счётчика × задержка
    "rate": 5.0,            # запросов счётчика в секунду (всего, на все аккаунты)
    "idle_poll": 30.0,      # секунд между проверками, пока улучшений нет
    "boost": True,          # экстра-режим у самой цели
    "boost_window": 10,     # за сколько номеров до цели включать экстра-режим
    "boost_rate": 10.0,     # проверок в секунду в экстра-режиме (10 = раз в 0,1 с)
    "slug": None,           # основа ссылки коллекции, напр. "PlushPepe"
    "keep_details": False,  # сохранять подпись отправителя на коллекционке
}
MAX_TARGETS = 10000

HELP = """🎯 Gift Sniper — команды (пишите здесь, в Избранном):

/status — что бот делает сейчас
/accounts — подключённые аккаунты
/gifts — подарки на всех аккаунтах, которые можно улучшить
/gift 1 3 — выбрать подарки №1 и №3 (залп), /gift all — все одной модели
/target 777 1000x2 1111-1115 — номера; x2 — сколько подарков на номер (по умолчанию 1)
/early 2 — за сколько номеров до цели стрелять, /early auto — само
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
    if "targets" in cfg:                          # формат до «плана»
        if "plan" not in json.loads(CONFIG.read_text() if CONFIG.exists() else "{}"):
            cfg["plan"] = [{"t": n, "n": 1} for n in cfg["targets"]]
        cfg.pop("targets")
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
    for a, b, single in re.findall(r"(\d+)\s*[-–—]\s*(\d+)|(\d+)", text):
        if single:
            nums.add(int(single))
        else:
            lo, hi = sorted((int(a), int(b)))
            nums.update(range(lo, hi + 1))
        if len(nums) > MAX_TARGETS:
            raise ValueError(f"слишком много номеров (больше {MAX_TARGETS})")
    nums.discard(0)
    return sorted(nums)


def parse_plan(text):
    """«777 1000x2 1111-1115» → [{t: 777, n: 1}, {t: 1000, n: 2}, {t: 1111, n: 1}, …].

    x2 / ×2 / *2 после номера или диапазона — сколько подарков тратить на номер.
    """
    plan = {}
    rx = r"(\d+)(?:\s*[-–—]\s*(\d+))?(?:\s*[xх×*]\s*(\d+))?"
    for a, b, n in re.findall(rx, text, flags=re.I):
        lo, hi = (int(a), int(b or a))
        lo, hi = min(lo, hi), max(lo, hi)
        for num in range(lo, hi + 1):
            if num > 0:
                plan[num] = max(1, min(100, int(n or 1)))
        if len(plan) > MAX_TARGETS:
            raise ValueError(f"слишком много номеров (больше {MAX_TARGETS})")
    return [{"t": k, "n": v} for k, v in sorted(plan.items())]


def clean_plan(items):
    """План из панели: список {t, n} → проверенный и отсортированный."""
    plan = {}
    for e in items:
        num, n = int(e["t"]), int(e.get("n", 1))
        if num > 0:
            plan[num] = max(1, min(100, n))
    if len(plan) > MAX_TARGETS:
        raise ValueError(f"слишком много номеров (больше {MAX_TARGETS})")
    return [{"t": k, "n": v} for k, v in sorted(plan.items())]


def plan_text(plan, limit=12):
    """«777, 1000×2, 1111–1115»: ×N — только если подарков на номер больше одного."""
    parts, i = [], 0
    while i < len(plan):
        j = i
        while (j + 1 < len(plan) and plan[j + 1]["t"] == plan[j]["t"] + 1
               and plan[j + 1]["n"] == plan[i]["n"]):
            j += 1
        a, b, n = plan[i]["t"], plan[j]["t"], plan[i]["n"]
        parts.append((str(a) if a == b else f"{a}–{b}") + (f"×{n}" if n > 1 else ""))
        i = j + 1
    text = ", ".join(parts[:limit]) or "—"
    return text + (f" … (+{len(parts) - limit})" if len(parts) > limit else "")


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
        self.pool = []                    # ещё не потраченные подарки этой охоты
        self.done = {}                    # номер → итог («поймал #…», «проскочил»)
        self.boost_for = None             # для какой цели уже включён экстра-режим
        self.catalog_hash = {}            # хэш каталога подарков по аккаунтам
        self.catalog_open = {}
        self.hist = collections.deque(maxlen=400)   # (время, значение счётчика)
        self.rtts = collections.deque(maxlen=50)    # задержки запросов счётчика, с
        self.forms = {}                   # заранее полученные формы оплаты
        self.pollers = []
        self.last_note = ""
        self.busy = False
        self.notifier = None              # отправка в чат бота-панели
        self.owner_ids = set()            # id наших аккаунтов (доступ к панели)
        self.main_id = None               # id главного аккаунта

    # ---------- общение ----------

    async def say(self, text, saved=False):
        """Уведомление: в чат бота-панели (если подключён), иначе в Избранное."""
        if self.notifier and not saved:
            try:
                await self.notifier(text)
                return
            except Exception:
                pass
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
                exclude_unique=True, exclude_unlimited=True))   # только лимитки
            result += r.gifts
            if not r.next_offset:
                return result
            offset = r.next_offset

    @staticmethod
    def label(gift):
        """«🧸 15⭐ · лимит 1200/5000» — как узнать подарок без названия."""
        emoji = ""
        for a in getattr(getattr(gift, "sticker", None), "attributes", []) or []:
            if isinstance(a, types.DocumentAttributeSticker) and a.alt:
                emoji = a.alt
        parts = [x for x in (emoji, getattr(gift, "title", None)) if x]
        parts.append(f"{getattr(gift, 'stars', '?')}⭐")
        if getattr(gift, "limited", False):
            total = gift.availability_total or "?"
            parts.append(f"лимитка, осталось {gift.availability_remains}/{total}")
        return " ".join(parts[:-1]) + " · " + parts[-1] if len(parts) > 1 else parts[0]

    @classmethod
    def describe(cls, sg, account):
        gift = sg.gift
        return {
            "account": account,
            "msg_id": sg.msg_id,
            "saved_id": sg.saved_id,
            "gift_id": gift.id,
            "label": cls.label(gift),
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
        """Ссылка на коллекционку №1: «PlushPepe-1». None — название неизвестно."""
        if self.cfg.get("slug"):
            return f"{self.cfg['slug']}-1"
        src = self.shots or self.cfg["gifts"]
        title = src[0]["title"] if src else ""
        if not title or title.startswith("Подарок "):   # у подарка нет названия
            return None
        return f"{slug_base(title)}-1"

    async def read_counter(self, acc):
        slug = self.collection_slug()
        if slug is None:
            raise ValueError("не знаю название коллекции — задайте его (/slug "
                             "НазваниеБезПробелов или поле в панели)")
        acc.requests += 1
        r = await acc.client(functions.payments.GetUniqueStarGiftRequest(slug=slug))
        return r.gift.availability_issued

    def boosting(self):
        """Экстра-режим: до ближайшей цели осталось не больше boost_window номеров."""
        cfg = self.cfg
        if not cfg.get("boost") or self.issued is None or self.phase != "hot":
            return False
        target = self.next_target(self.issued)
        return target is not None and target - self.issued <= cfg["boost_window"]

    def speed(self):
        """Сколько номеров в секунду улучшают сейчас (по последним ~3 с)."""
        now = time.monotonic()
        pts = [(t, v) for t, v in self.hist if now - t <= 3]
        if len(pts) < 2 or pts[-1][0] - pts[0][0] < 0.3:
            return 0.0
        return max(0.0, (max(v for _, v in pts) - pts[0][1]) / (pts[-1][0] - pts[0][0]))

    def rtt(self):
        return statistics.median(self.rtts) if self.rtts else 0.05

    def early_now(self):
        """Упреждение: сколько чужих улучшений пройдёт, пока наш запрос в пути."""
        if self.cfg.get("early_auto", True):
            return int(round(self.speed() * self.rtt()))
        return self.cfg["early"]

    def effective_rate(self):
        cfg = self.cfg
        if self.boosting():
            return max(cfg["rate"], cfg["boost_rate"])
        return cfg["rate"]

    async def poller(self, acc, offset):
        """Каждый аккаунт опрашивает счётчик в своё окно, вместе — rate в секунду."""
        await asyncio.sleep(offset)
        while self.phase == "hot":
            interval = len(self.accounts) / max(self.effective_rate(), 0.01)
            now = time.monotonic()
            if now < acc.cooldown_until:
                await asyncio.sleep(min(acc.cooldown_until - now, 5))
                continue
            try:
                t0 = time.monotonic()
                value = await self.read_counter(acc)
                now = time.monotonic()
                self.rtts.append(now - t0)
                self.hist.append((now, value))
                self.issued = max(self.issued or 0, value)
                self.counter_error = None
            except FloodWaitError as e:
                acc.floods += 1
                acc.cooldown_until = time.monotonic() + e.seconds + 1
                await self.say(f"⏳ [{acc.name}] Telegram просит паузу {e.seconds} с "
                               "— этот аккаунт отдыхает, остальные работают. "
                               "Если такое часто — уменьшите /rate.")
            except (RPCError, ValueError) as e:
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

    async def prepare_all(self, gifts=None):
        await asyncio.gather(*(self.prepare_form(i) for i in (gifts or self.shots)),
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

    async def fire_all(self, gifts=None):
        """Залп: подарки улучшаются одновременно."""
        return await asyncio.gather(*(self.fire_one(i) for i in (gifts or self.shots)))

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
                wanted = num in self.plan_targets()
                mark = "🎉" if wanted else "•"
                hit |= wanted
                lines.append(f"{mark} {who}: #{num} ({ms:.0f} мс)")
        head = ("🎉 ПОЙМАЛ!" if hit else
                f"Залп выполнен{f', цель была #{target}' if target else ''}:")
        return head + "\n" + "\n".join(lines)

    # ---------- главный цикл ----------

    def plan_targets(self):
        return {e["t"] for e in self.cfg["plan"]}

    def pending(self):
        return [e for e in self.cfg["plan"] if e["t"] not in self.done]

    def next_target(self, issued):
        for e in self.pending():
            if e["t"] > issued:
                return e["t"]
        return None

    def summary(self):
        lines = ["📋 Итог охоты:"]
        for e in self.cfg["plan"][:40]:
            lines.append(f"• #{e['t']}: {self.done.get(e['t'], 'не стреляли')}")
        if self.pool:
            lines.append(f"Не потрачено подарков: {len(self.pool)}")
        return "\n".join(lines)

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
        if (not cfg["enabled"] or self.busy
                or (not cfg["gifts"] and self.phase != "hot")):
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
            if isinstance(self.counter_error, ValueError):
                await self.note_once(f"⚠️ {self.counter_error}")
            elif self.counter_error:
                await self.note_once(
                    "🔎 Коллекция ещё не появилась (никто не улучшил первым) "
                    f"или ссылка «{self.collection_slug()}» не та. Жду… "
                    "Если долго так — задайте /slug.")
            await asyncio.sleep(0.05)
            return
        # номера, которые счётчик уже проскочил, а мы не стреляли
        missed = [e["t"] for e in self.pending() if e["t"] <= self.issued]
        for num in missed:
            self.done[num] = f"проскочил (счётчик уже {self.issued}), подарок сохранён"
        if missed:
            await self.say(f"⚠️ Проскочили: {', '.join(map(str, missed[:20]))}. "
                           "Их подарки остаются для следующих номеров.")
        entry = next((e for e in self.pending() if e["t"] > self.issued), None)
        if entry is None or not self.pool:
            self.finish()
            why = ("все номера отработаны" if entry is None else
                   "подарки закончились")
            await self.say(f"🏁 Охота завершена: {why}.\n" + self.summary())
            return
        target = entry["t"]
        batch = self.pool[:entry["n"]]
        if self.boosting() and self.boost_for != target:
            self.boost_for = target
            await self.say(f"⚡ Экстра-режим: до #{target} осталось "
                           f"{target - self.issued}, проверяю счётчик "
                           f"{self.effective_rate():g} раз/с.")
        gap = target - (self.issued + 1)       # сколько номеров до цели
        early = self.early_now()
        if gap <= early + 30:
            await self.prepare_all(batch)       # оплату готовим заранее
        if gap <= early:
            self.pool = self.pool[len(batch):]
            results = await self.fire_all(batch)
            got = [num for _, num, _, err in results if num and not err]
            self.done[target] = (f"🎉 поймал #{target}" if target in got else
                                 "выстрел: " + (", ".join(f"#{n}" for n in got) or "номер не прочитан"))
            for num in got:                     # попали в другой номер из плана
                if num != target and num in self.plan_targets() and num not in self.done:
                    self.done[num] = f"🎉 поймал #{num} (залпом на #{target})"
            fired = {self.key(i) for i in batch}
            cfg["gifts"] = [g for g in cfg["gifts"] if self.key(g) not in fired]
            save_config(cfg)
            await self.say(self.report(results, target) +
                           f"\nОсталось подарков: {len(self.pool)}, номеров: "
                           f"{len([e for e in self.pending() if e['t'] > self.issued])}")
            return
        await asyncio.sleep(min(0.5, max(0.002, 0.5 / max(self.effective_rate(), 1))))

    async def release_seen(self, acc, gift_ids):
        """Есть ли у этих моделей цена улучшения в каталоге Telegram (= улучшения вышли).

        Каталог запрашивается с хэшем: если ничего не менялось, ответ пустой и лёгкий.
        """
        r = await acc.client(functions.payments.GetStarGiftsRequest(
            hash=self.catalog_hash.get(acc.name, 0)))
        if isinstance(r, types.payments.StarGiftsNotModified):
            return self.catalog_open.get(acc.name, False)
        self.catalog_hash[acc.name] = r.hash
        is_open = any(getattr(g, "id", None) in gift_ids and getattr(g, "upgrade_stars", None)
                      for g in r.gifts)
        self.catalog_open[acc.name] = is_open
        return is_open

    async def watch_release(self, gift_ids):
        """Аккаунты по очереди смотрят каталог; полный круг — idle_poll секунд."""
        accs = list(self.accounts.values())
        step = self.cfg["idle_poll"] / len(accs)
        for acc in accs:
            await asyncio.sleep(step)
            if not self.cfg["enabled"]:
                return
            if time.monotonic() < acc.cooldown_until:
                continue
            try:
                acc.requests += 1
                if await self.release_seen(acc, gift_ids):
                    return            # сразу перепроверим подарки на главном аккаунте
            except FloodWaitError as e:
                acc.floods += 1
                acc.cooldown_until = time.monotonic() + e.seconds + 1
            except RPCError:
                pass

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
            n = len(self.accounts)
            await self.note_once(
                f"🕐 Жду выхода улучшений ({len(waiting)} подарк.). Каждый из {n} "
                f"аккаунт(ов) проверяет раз в {cfg['idle_poll']:.0f} с, вместе — "
                f"примерно раз в {cfg['idle_poll'] / n:.0f} с.")
            await self.watch_release({w["gift_id"] for w in waiting})
            return
        self.shots, self.issued, self.forms = ready, None, {}
        self.pool, self.done, self.boost_for = list(ready), {}, None
        self.hist.clear()
        self.rtts.clear()
        self.phase = "hot"
        self.start_pollers()
        need = sum(e["n"] for e in cfg["plan"])
        warn = (f"\n⚠️ Подарков ({len(ready)}) меньше, чем нужно по плану ({need}): "
                "последним номерам может не хватить." if need > len(ready) else "")
        await self.say(f"🔥 Улучшения доступны! Подарков готово: {len(ready)}. "
                       f"Номера: {plan_text(cfg['plan'])}. Упреждение: "
                       f"{'авто' if cfg.get('early_auto', True) else cfg['early']}, счётчик — "
                       f"{cfg['rate']:g} запр/с на {len(self.accounts)} аккаунт(а).{warn}")

    # ---------- команды ----------

    async def on_command(self, event):
        text = event.raw_text.strip()
        cmd, _, arg = text.partition(" ")
        cmd = cmd.lower().split("@")[0]
        cfg = self.cfg
        say = self.say
        self.say = lambda text: say(text, saved=True)
        try:
            if cmd in ("/help", "/start"):
                await self.say(HELP)
            elif cmd == "/status":
                await self.say(self.status_text())
            elif cmd == "/accounts":
                await self.say(await self.cmd_accounts())
            elif cmd == "/gifts":
                await self.say(await self.cmd_gifts())
            elif cmd == "/gift":
                await self.say(await self.cmd_gift(arg))
            elif cmd == "/target":
                plan = parse_plan(arg)
                if not plan:
                    raise ValueError("укажите номер: /target 777 1000x2 1111-1115")
                cfg["plan"] = plan
                save_config(cfg)
                await self.say(f"🎯 Номера ({len(plan)}): {plan_text(plan)}\n"
                               f"Нужно подарков: {sum(e['n'] for e in plan)}")
            elif cmd == "/early":
                if arg.strip().lower() in ("auto", "авто"):
                    cfg["early_auto"] = True
                    msg = "⏱ Упреждение считается автоматически."
                else:
                    cfg["early"], cfg["early_auto"] = max(0, int(arg)), False
                    msg = f"⏱ Стреляю за {cfg['early']} номер(а) до цели."
                save_config(cfg)
                await self.say(msg)
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
                await self.say(f"🔗 Коллекция: {self.collection_slug() or 'не задана'}")
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
                await self.say(await self.cmd_ping())
            elif cmd == "/test":
                await self.say(await self.cmd_test())
            elif cmd == "/now":
                await self.say(await self.cmd_now())
        except Exception as e:
            await self.say(f"⚠️ {e}")
        finally:
            self.say = say

    def status_text(self):
        cfg = self.cfg
        lines = [
            f"Охота: {'включена ✅' if cfg['enabled'] else 'выключена ⏹'} (этап: {self.phase})",
            f"Аккаунтов: {len(self.accounts)}",
            f"Подарков в залпе: {len(cfg['gifts'])}"
            + (f" — {cfg['gifts'][0]['title']}" if cfg["gifts"] else " (выберите: /gifts)"),
            f"Номера: {plan_text(cfg['plan'])} (нужно подарков: "
            f"{sum(e['n'] for e in cfg['plan'])})",
            f"Упреждение: {'авто' if cfg.get('early_auto', True) else cfg['early']} · счётчик {cfg['rate']:g} запр/с · "
            f"ожидание раз в {cfg['idle_poll']:g} с",
            ("Экстра-режим: " + (f"за {cfg['boost_window']} номеров до цели — "
                                 f"{cfg['boost_rate']:g} проверок/с" if cfg["boost"] else "выключен")),
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
        return "\n".join(lines)

    async def cmd_gifts(self):
        gifts = []
        for acc in self.accounts.values():
            gifts += [self.describe(sg, acc.name) for sg in await self.saved_gifts(acc)]
        self.gift_list = gifts
        if not gifts:
            return "Подарков, которые можно улучшить, не найдено."
        # одинаковые подарки (модель + аккаунт + состояние) — одной строкой
        groups = {}
        for i, d in enumerate(gifts, 1):
            k = (d["gift_id"], d["account"], d["can_upgrade"], d["prepaid"],
                 d["gift_num"])
            groups.setdefault(k, []).append(i)
        lines = ["Подарки (выбор: /gift 3, /gift 1 3, /gift all 3 — все той же модели):"]
        for (gid, acc, can, pre, num), idx in groups.items():
            d = gifts[idx[0] - 1]
            nums = (f"{idx[0]}" if len(idx) == 1 else
                    f"{idx[0]}–{idx[-1]}" if idx[-1] - idx[0] == len(idx) - 1 else
                    ", ".join(map(str, idx)))
            extra = [f"номер уже #{num}"] if num else []
            extra.append("улучшение доступно" if can else "улучшений пока нет")
            if pre:
                extra.append("оплачено")
            count = f" ×{len(idx)}" if len(idx) > 1 else ""
            lines.append(f"{nums}. [{acc}] {d['label']}{count} — " + ", ".join(extra)
                         + f"\n    id {gid}")
        return "\n".join(lines)

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
        return "\n".join(lines)

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
        return "\n".join(lines)

    async def cmd_test(self):
        if not self.cfg["gifts"]:
            raise ValueError("сначала выберите подарки: /gifts, потом /gift N")
        lines = []
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
        counts = {}
        for line in lines:
            line = re.sub(r"форма оплаты за \d+ мс", "форма оплаты готова", line)
            counts[line] = counts.get(line, 0) + 1
        lines = ["🧪 Пробный прогон (без улучшения):"] + [
            line + (f" ×{n}" if n > 1 else "") for line, n in counts.items()]
        try:
            t0 = time.monotonic()
            issued = await self.read_counter(self.main)
            lines.append(f"• счётчик «{self.collection_slug()}»: {issued} "
                         f"({(time.monotonic() - t0) * 1000:.0f} мс)")
        except ValueError as e:
            lines.append(f"• счётчик: {e}")
        except RPCError as e:
            lines.append(f"• счётчик «{self.collection_slug()}» недоступен "
                         f"({e.__class__.__name__}): коллекции ещё нет или название не то")
        return "\n".join(lines)

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
        return self.report(results)


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
    for acc in accounts.values():
        sniper.owner_ids.add((await acc.client.get_me()).id)
    sniper.main_id = (await sniper.main.client.get_me()).id

    @sniper.main.client.on(events.NewMessage(chats="me", pattern=r"^/"))
    async def _(event):
        await sniper.on_command(event)

    import buyer
    sniper.buyer = buyer.Buyer(sniper, cfg, save_config)
    await sniper.buyer.refresh_balance()
    tasks = [sniper.main.client.run_until_disconnected(), sniper.loop(),
             sniper.buyer.loop()]
    hello = ""
    if cfg.get("panel"):
        try:
            import panel
            bot_client = await panel.Panel(sniper, cfg).start()
            tasks.append(bot_client.run_until_disconnected())
            hello = "\nПанель: кнопка «Панель» в чате вашего бота."
        except Exception as e:
            hello = f"\n⚠️ Панель не запустилась: {e!r}"

    await sniper.say(f"🤖 Gift Sniper запущен, аккаунтов: {len(accounts)}. "
                     f"/help — команды.{hello}\n\n" + sniper.status_text())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
