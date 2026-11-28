"""Автопокупка новых подарков из каталога Telegram на главный аккаунт.

- Каталог (payments.getStarGifts с хэшем) по очереди смотрят все аккаунты;
  полный круг — buy.poll секунд на аккаунт.
- При включении запоминается всё, что уже есть в каталоге: покупаются только
  подарки, которые появились ПОСЛЕ включения.
- Фильтр — блоки rules: [{min, max, count}] — «от min до max ⭐ покупать по count шт.»
  (блоков сколько угодно; если диапазоны пересекаются, берётся блок с меньшим min).
  По желанию только лимитированные; аукционы и распроданные пропускаются.
- Бюджет: всего не больше budget ⭐ (счётчик spent), иначе покупка пропускается.
- Покупает главный аккаунт себе: getPaymentForm(inputInvoiceStarGift) +
  sendStarsForm, штуки одного подарка — параллельно.
"""

import asyncio
import collections
import time

from telethon.errors import FloodWaitError, RPCError
from telethon.tl import functions, types

TEDDY_ID = 5170233102089322756          # 🧸 за 15⭐ — для тестовой покупки

BUY_DEFAULTS = {
    "enabled": False,
    "rules": None,          # блоки [{min, max, count}]: цена от/до ⭐, сколько штук
    "budget": 1000,         # всего можно потратить, ⭐
    "spent": 0,             # уже потрачено автопокупкой, ⭐
    "poll": 10.0,           # каждый аккаунт смотрит каталог раз в N секунд
    "limited_only": True,   # только лимитированные
    "known": None,          # id подарков, которые уже были в каталоге
}


class Buyer:
    def __init__(self, sniper, cfg, save):
        self.s = sniper
        self.cfg = cfg
        self.save = save
        b = cfg.setdefault("buy", {})
        for k, v in BUY_DEFAULTS.items():
            b.setdefault(k, v)
        if b["rules"] is None:                # перенос старых настроек в первый блок
            b["rules"] = [{"min": b.pop("min", 1), "max": b.pop("max", 1000),
                           "count": b.pop("count", 1)}]
        self.hash = {}                        # хэш каталога по аккаунтам
        self.log = collections.deque(maxlen=30)
        self.balance = None
        self.last_check = None
        self.lock = asyncio.Lock()

    @property
    def b(self):
        return self.cfg["buy"]

    # ---------- каталог ----------

    async def catalog(self, acc, fresh=False):
        """Список подарков каталога или None, если с прошлого раза ничего не менялось."""
        r = await acc.client(functions.payments.GetStarGiftsRequest(
            hash=0 if fresh else self.hash.get(acc.name, 0)))
        acc.requests += 1
        if isinstance(r, types.payments.StarGiftsNotModified):
            return None
        self.hash[acc.name] = r.hash
        return [g for g in r.gifts if isinstance(g, types.StarGift)]

    def rule_for(self, g):
        """Блок, под который подходит подарок, или None."""
        b = self.b
        if g.sold_out or getattr(g, "auction", False):
            return None
        if b["limited_only"] and not g.limited:
            return None
        return next((r for r in b["rules"] if r["min"] <= g.stars <= r["max"]), None)

    # ---------- покупка ----------

    async def buy_one(self, gift_id):
        client = self.s.main.client
        invoice = types.InputInvoiceStarGift(peer=types.InputPeerSelf(), gift_id=gift_id)
        form = await client(functions.payments.GetPaymentFormRequest(invoice=invoice))
        await client(functions.payments.SendStarsFormRequest(
            form_id=form.form_id, invoice=invoice))

    async def buy(self, g, count, test=False):
        t0 = time.monotonic()
        res = await asyncio.gather(*(self.buy_one(g.id) for _ in range(count)),
                                   return_exceptions=True)
        ok = sum(1 for r in res if not isinstance(r, Exception))
        errs = [r for r in res if isinstance(r, Exception)]
        if not test:
            self.b["spent"] += ok * g.stars
            self.save(self.cfg)
        label = self.s.label(g)
        self.log.appendleft({"t": time.strftime("%d.%m %H:%M"), "label": label,
                             "ok": ok, "of": count, "stars": ok * g.stars, "test": test,
                             "err": str(errs[0]) if errs else None})
        ms = (time.monotonic() - t0) * 1000
        text = (f"🛒 {'Тестовая покупка' if test else 'Куплено'}: {label} — "
                f"{ok} из {count} шт., потрачено {ok * g.stars}⭐ ({ms:.0f} мс)")
        if errs:
            text += f"\n⚠️ Ошибка: {errs[0]}"
        if not test:
            text += f"\nПотрачено всего: {self.b['spent']} из {self.b['budget']}⭐"
        await self.s.say(text)
        await self.refresh_balance()
        return text

    async def consider(self, g):
        """Новый подарок в каталоге: купить, если подходит под фильтр и бюджет."""
        rule = self.rule_for(g)
        if rule is None:
            return
        b = self.b
        count = rule["count"]
        if g.limited_per_user and g.per_user_remains is not None:
            count = min(count, g.per_user_remains)
        left = b["budget"] - b["spent"]
        count = min(count, left // g.stars) if g.stars else count
        if count <= 0:
            await self.s.say(f"💸 Вышел подходящий подарок {self.s.label(g)}, но не хватает "
                             f"бюджета: осталось {max(0, left)}⭐ из {b['budget']}⭐. Не покупаю.")
            return
        await self.buy(g, count)

    # ---------- цикл ----------

    async def baseline(self):
        gifts = await self.catalog(self.s.main, fresh=True)
        self.b["known"] = sorted(g.id for g in gifts)
        self.save(self.cfg)
        await self.s.say(f"🛒 Автопокупка включена. Сейчас в каталоге {len(gifts)} "
                         "подарков — их не трогаю, жду новые.")

    async def loop(self):
        while True:
            try:
                if not self.b["enabled"]:
                    await asyncio.sleep(1)
                    continue
                if self.b["known"] is None:
                    await self.baseline()
                await self.round()
            except Exception as e:      # цикл покупок не должен падать
                await self.s.note_once(f"⚠️ Автопокупка: {e!r}")
                await asyncio.sleep(5)

    async def round(self):
        accs = list(self.s.accounts.values())
        step = max(0.2, self.b["poll"] / len(accs))
        for acc in accs:
            await asyncio.sleep(step)
            if not self.b["enabled"] or self.b["known"] is None:
                return
            if time.monotonic() < acc.cooldown_until:
                continue
            try:
                gifts = await self.catalog(acc)
            except FloodWaitError as e:
                acc.floods += 1
                acc.cooldown_until = time.monotonic() + e.seconds + 1
                continue
            except RPCError:
                continue
            self.last_check = time.time()
            if gifts is None:
                continue
            async with self.lock:
                known = set(self.b["known"])
                new = [g for g in gifts if g.id not in known]
                if not new:
                    continue
                self.b["known"] = sorted(known | {g.id for g in gifts})
                self.save(self.cfg)
                names = ", ".join(self.s.label(g) for g in new[:5])
                await self.s.say(f"🆕 В каталоге новые подарки: {names}")
                for g in new:
                    await self.consider(g)

    # ---------- для панели ----------

    async def refresh_balance(self):
        try:
            r = await self.s.main.client(functions.payments.GetStarsStatusRequest(
                peer=types.InputPeerSelf()))
            self.balance = r.balance.amount
        except Exception:
            pass
        return self.balance

    async def test_buy(self):
        gifts = await self.catalog(self.s.main, fresh=True)
        g = next((x for x in gifts if x.id == TEDDY_ID and not x.sold_out), None) or \
            next((x for x in gifts if x.stars == 15 and not x.limited and not x.sold_out), None)
        if g is None:
            raise ValueError("мишки за 15⭐ нет в каталоге")
        return await self.buy(g, 1, test=True)

    def set_enabled(self, on):
        self.b["enabled"] = bool(on)
        self.b["known"] = None          # при включении — заново запомнить каталог
        self.save(self.cfg)

    def apply(self, body):
        b = self.b
        if "rules" in body:
            rules = []
            for r in body["rules"]:
                lo_, hi_ = sorted((int(r["min"]), int(r["max"])))
                rules.append({"min": max(1, lo_), "max": min(10**7, hi_),
                              "count": max(1, min(1000, int(r.get("count", 1))))})
            if not rules:
                raise ValueError("нужен хотя бы один блок")
            b["rules"] = sorted(rules, key=lambda r: (r["min"], r["max"]))
        for key, lo, hi, cast in (("budget", 0, 10**7, int), ("poll", 2, 3600, float)):
            if key in body:
                b[key] = max(lo, min(hi, cast(float(body[key]))))
        if "limited_only" in body:
            b["limited_only"] = bool(body["limited_only"])
        if body.get("reset_spent"):
            b["spent"] = 0
        self.save(self.cfg)

    def state(self):
        b = self.b
        return {k: b[k] for k in ("enabled", "rules", "budget", "spent",
                                  "poll", "limited_only")} | {
            "known": len(b["known"]) if b["known"] is not None else None,
            "balance": self.balance,
            "last_check": int(time.time() - self.last_check) if self.last_check else None,
            "log": list(self.log),
            "accounts": len(self.s.accounts),
        }
