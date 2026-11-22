# Идеи роликов — 2026-11-03

Источник моделей: api.changes.tg через `engine/gifts_api.py`, выборка 2026-11-03:
124 коллекции, 7942 модели. Редкость — поле `rarity` API (в %). Принадлежность
моделей к теме проверена по PNG-превью, а не только по названию.
Цены, тиражи и число владельцев здесь **не проверены**: запрашивать перед сценарием.

## 1. Пепе: от комикса до подарков (основной кандидат)

Сюжет: «Создатель похоронил эту лягушку в 2017-м. А в Telegram она прячется
почти в трёх десятках коллекций».

1. 2005 — Мэтт Фьюри, комикс Boy's Club, MySpace; фраза «Feels good man».
2. Распространение через Myspace, Gaia Online, 4chan; превращение в мем.
3. 2016–2017 — присвоение мема радикалами (коротко, нейтрально); 6 мая 2017
   на Free Comic Book Day Фьюри «хоронит» Пепе; затем кампания Save Pepe.
4. Подарок Plush Pepe: релиз 2024-11-30, улучшение с 2025-01-01 (поля
   `releasedAt`/`upgradableAt` API). 50 моделей: черепашки-ниндзя (Leonardo,
   Donatello, Raphael, Ninja Mike), модные дома (Gucci Leap, Louis Vuittoad),
   футбол (Barcelona, Bavaria, Birmingham, Milano), Midas Pepe и др.
5. Реклама RubUp — с открытым вопросом «где ещё прячется Пепе?».
6. Охота по коллекциям: самые редкие — Cryo Pepe (Ice Cream, 0,1%),
   Meme God (Spring Basket, 0,1%), Pepe Hop (Jester Hat, 0,2%).
7. Финал: модель Plush Pepe внутри коллекции Resistance Dog (1,2%) — Пепе в Пепе.

Модели с Пепе вне коллекции Plush Pepe (27, подтверждены превью):

| Редкость | Модель — коллекция |
|---|---|
| 0,1% | Cryo Pepe — Ice Cream; Meme God — Spring Basket |
| 0,2% | Pepe Hop — Jester Hat |
| 0,3% | Pepe Plans — Desk Calendar; Pepe Diary — Star Notepad; Pepe Feels — Tama Gadget; Froggy — Bunny Muffin |
| 0,5% | Happy Pepe — Kissed Frog; Pepe Bag — Loot Bag; Festive Pepe — Winter Wreath; Pepe Frost — Snow Globe; Pepe Bag — Joyful Bundle; Pepe Surfer — Surge Board |
| 0,6–0,9% | Pepe Pryanik — Ginger Cookie; Pepe Pod — Restless Jar; Le Pepe — Party Sparkler |
| 1–1,3% | Shy Pepe — Jack-in-the-Box; Pepe Love — Cupid Charm; Pool Pepe — Pool Float; Froges — Timeless Book; Pepe Dream — Durov's Glasses; Plush Pepe — Resistance Dog |
| 1,5–3% | Pepe Band — Nail Bracelet; Pepe Socks — Fresh Socks; Froge Ring — Bonded Ring; Boiled Pepe — Easter Egg; Pepe Paws — Scared Cat |

Спорные (по превью не Пепе или не очевидно): Pepe Mania, Pepelicious,
Little Pepe, Crazy Frog (надпись Happy B-day), Pepelatz (отсылка к «Кин-дза-дза»).

Источники истории (получены 2026-11-03):
[CBS News](https://www.cbsnews.com/amp/news/pepe-the-frog-dead-cartoonist-matt-furie-boys-club-comic-book),
[The FADER](https://www.thefader.com/2017/05/08/pepe-the-frog-killed-off),
[Lambiek](https://www.lambiek.net/artists/f/furie_matt.htm).
Рынок Plush Pepe (рекорд 107 000 TON, подарок Дурову и т. п.) — только из
вторичных источников ([U.Today](https://u.today/plush-pepes-premium-telegram-gifts-drop-sees-floor-prices-targeting-5000-ton),
[vc.ru](https://vc.ru/telegram/2221885-rost-tsen-na-podarki-telegram)); перед
использованием сверить с датированными данными рынка.

## 2. Музей интернет-мемов в Telegram

Doge (Little Doge, Strong Doge, Doge Gem, DOGE, Dogel Mogel), Trollface (King Troll —
Victory Medal, 0,2%), Stonks (Pool Float), Nyan Cat (×3), Skibidi Toilet
(Money Pot, 0,1%), Amogus (Jack-in-the-Box). Формат: «зал славы» — каждый мем
с годом рождения и подарком.

## 3. Пасхалки про Дурова

Pavel Durov (Big Year, цифры «1984»), Durov Duck (Love Potion), Durov's Dog
(Bow Tie), Durov Day (Desk Calendar), Durov's Cap внутри Pet Snake,
коллекция Durov's Glasses. Вопрос: «Сколько раз Дуров спрятал себя в подарках?»

## 4. Крипта в подарках

Satoshi (Resistance Dog, crafted), Bitcoin (×6), Bitcoinicle (Myth Mask, crafted),
Crypto Whale (×2), Diamond Hands, Hodler, To The Moon (×4), TON-модели.
Смысл поля `crafted` и нулевой редкости — не проверено.

## 5. Барбенгеймер

Девять моделей Barbie и одна Oppenheimer (Liberty Figure, 1%) — сюжет 2023 года
в подарках.

## 6. Русские пасхалки

Pepelatz (Stellar Rocket), Pepe Pryanik, Dogel Mogel, Brick 3310 (Artisan Brick).

## 7. Мультфильмы

Pickle Rick (×2), Homer (×3), Simpsonic, Shrek (×2), Spiderman, Mario Cake/Mario Pipe.

## 8. Маски: коллекция Myth Mask (выбрано автором для изучения 2026-11-03)

Данные API на 2026-11-03: выпуск 2025-10-31 (Хэллоуин), улучшение с 2026-10-31
15:09 UTC (`upgradableAt`, источник «telegram»; вторым источником не подтверждено).
134 модели, 80 фонов, 262 символа. 33 модели помечены `crafted` с редкостью 0%
и уровнями legendary/epic/rare/uncommon — как их получают, **не проверено**.
Тираж, цены и число владельцев **не проверены**.

Самые редкие обычные модели: Dark Knight и Night Howler (0,1%), затем 20 моделей
по 0,2%. Crafted legendary: Bitcoinicle, Fatality.

Отсылки, опознанные по превью (уверенно):

| Тема | Модели |
|---|---|
| Кино-хоррор | Ghostface (Крик, 1,1%), Billy Puppet (Пила, 0,2%), Hannibal (0,2%), Neon Purge (Судная ночь, 1%), Pumpkin Jack |
| Кино и сериалы | Anonymous (V — значит вендетта, 1%), Bella Ciao (Бумажный дом, 0,6%), Frontman (Игра в кальмара, crafted), Arthur Fool (Джокер 2019, 0,9%), Backbreaker (Бэйн, 0,9%), Dark Knight (Бэтмен, 0,1%), Cuban Pete (Маска 1994, 1,4%), Witch King (Властелин колец, 1,4%), Baldwin (Царство небесное, 0,2%), No Face (Унесённые призраками, 1,4%), Zorro (1%), The Donald (0,2%) |
| Игры | Enderman (Minecraft), Little Ghost и Horny (Hollow Knight), Death Blossom (Жнец, Overwatch), Wasteland (Borderlands), Deadly Hug (Poppy Playtime) |
| Музыка | ALL CAPS (MF DOOM, 1%) |
| Традиции | Plague Doctor, Dark Masquerade, Royal/Twisted Jester (Венеция); Kitsune, Red Oni (Япония); La Muerte (Мексика); Tiki Mana; Pharaoh, Anubis, Golden Ra (Египет); Apollo, Venus, Medusa, Marble David (античность); Tragic Muse, Tragic Face (театр); Dragon Dance (Китай); Mayan Mask, Tribal Warrior |

Предположительно (проверить): Predator, Doomsday (Доктор Дум), Wrong Number и
Wild Stallion (Hotline Miami), Monkey Heist (Payday), Night Howler (Зверополис),
Liquid Metal (Терминатор 2), Fatality (Mortal Kombat).

Маски в других коллекциях: Scream (Mini Oscar, 1,5%), Gas Mask (Mini Oscar, 1%),
Jason (Jolly Chimp, 1,5%), The Mask (Mad Pumpkin, 1%), Anonymous (Resistance Dog, 0,9%),
Mystery Mask (Jester Hat, 0,5%), Twin Faces (Lucky Locket, 3%).

Факты для подачи (получены 2026-11-03):
- Латинское persona сначала означало театральную маску; затем «роль», «лицо»,
  «человек» ([Etymonline](https://www.etymonline.com/word/persona)).
- Маску Гая Фокса нарисовал Дэвид Ллойд для комикса V for Vendetta (1982, журнал
  Warrior); после фильма её массово выпускала Warner Bros.; в 2008 году Anonymous
  надели её на протестах против Церкви саентологии (Project Chanology), 10 февраля
  2008 — более 7000 человек в 100+ городах ([Wikipedia](https://en.wikipedia.org/wiki/Guy_Fawkes_mask),
  [CNBC](https://www.cnbc.com/2015/12/29/the-man-behind-the-anonymous-mask-v-for-vendettas-david-lloyd.html)).
- История чумного доктора и прочих традиций — **не проверено**, искать отдельно.

### Пятёрка масок для ролика (2026-11-03)

Критерий: самые узнаваемые фильмы и персонажи, опознание по превью уверенное.
Анимации проверены через `lottie_strip.py`: у всех 180 кадров, 60 fps, цикл 3 с,
альфа непустая, кадры меняются.

1. Ghostface (1,1%) — «Крик»; в цикле маска заливается кровью (≈1,2–2,1 с).
2. Anonymous (1%) — «V — значит вендетта»; в цикле летят алые розы — знак V.
3. Bella Ciao (0,6%) — «Бумажный дом»; маска Дали.
4. Arthur Fool (0,9%) — «Джокер» (2019), клоунская маска.
5. Dark Knight (0,1%) — Бэтмен; в цикле вылетают летучие мыши; самая редкая из пяти.

Запас: Billy Puppet («Пила», 0,2%), Frontman («Игра в кальмара», crafted).

## Красивые сочетания «модель + фон» до 30 000 ₽ (2026-11-22)

Источник: fragment.com, лоты «в продаже», самый дешёвый лот с этой моделью и фоном на 2026-11-22; курс 1 TON = 76,65 ₽ (tonapi.io).
Отбор: цвета всех 7644 моделей (api.changes.tg) сравнены с цветами фонов, 708 лучших пар проверены на Fragment, 105 найдены в продаже, 29 отобраны глазами.
Данные: [data/beautiful_combos_2026-11-22.json](data/beautiful_combos_2026-11-22.json). Цены меняются — перед роликом перепроверить.

| Группа | Подарок | Модель / фон | TON | ₽ | Лот |
|---|---|---|---|---|---|
| В цвет фона | Clover Pin | Celtic Knot / Old Gold | 10 | 770 | [cloverpin-54010](https://fragment.com/gift/cloverpin-54010) |
| В цвет фона | Instant Ramen | Arcane Bowl / Navy Blue | 10 | 770 | [instantramen-254427](https://fragment.com/gift/instantramen-254427) |
| В цвет фона | Clover Pin | Lollipop / Burgundy | 11 | 840 | [cloverpin-131518](https://fragment.com/gift/cloverpin-131518) |
| В цвет фона | Instant Ramen | First Date / Purple | 14 | 1070 | [instantramen-254415](https://fragment.com/gift/instantramen-254415) |
| В цвет фона | Lol Pop | Dark Sky / Cobalt Blue | 15 | 1150 | [lolpop-304637](https://fragment.com/gift/lolpop-304637) |
| В цвет фона | Clover Pin | Ruby Clover / Strawberry | 25 | 1920 | [cloverpin-110367](https://fragment.com/gift/cloverpin-110367) |
| В цвет фона | Stellar Rocket | Green Jelly / Mint Green | 25 | 1920 | [stellarrocket-55603](https://fragment.com/gift/stellarrocket-55603) |
| В цвет фона | Lunar Snake | Timelock / Emerald | 28 | 2150 | [lunarsnake-113422](https://fragment.com/gift/lunarsnake-113422) |
| В цвет фона | Victory Medal | Viking / Amber | 40 | 3070 | [victorymedal-24032](https://fragment.com/gift/victorymedal-24032) |
| В цвет фона | Snoop Dogg | Black Diamond / Electric Indigo | 45 | 3450 | [snoopdogg-152219](https://fragment.com/gift/snoopdogg-152219) |
| В цвет фона | Homemade Cake | Pink Velvet / Purple | 50 | 3830 | [homemadecake-99997](https://fragment.com/gift/homemadecake-99997) |
| В цвет фона | Liberty Figure | Ruby Flame / Strawberry | 55 | 4220 | [libertyfigure-105101](https://fragment.com/gift/libertyfigure-105101) |
| В цвет фона | Witch Hat | Nebula Mist / Electric Purple | 99 | 7590 | [witchhat-44144](https://fragment.com/gift/witchhat-44144) |
| В цвет фона | Bonded Ring | Anaconda / Dark Green | 120 | 9200 | [bondedring-1493](https://fragment.com/gift/bondedring-1493) |
| В цвет фона | Toy Bear | Chocolate / Amber | 150 | 11500 | [toybear-13540](https://fragment.com/gift/toybear-13540) |
| Контраст | Mirage Lamp | Ruby Moon / Deep Cyan | 15 | 1150 | [miragelamp-44421](https://fragment.com/gift/miragelamp-44421) |
| Контраст | Bow Tie | Cherries / Deep Cyan | 22 | 1690 | [bowtie-11962](https://fragment.com/gift/bowtie-11962) |
| Контраст | Bling Binky | Violetta / Mint Green | 35 | 2680 | [blingbinky-7897](https://fragment.com/gift/blingbinky-7897) |
| Контраст | Voodoo Doll | Jellousy / Grape | 65 | 4980 | [voodoodoll-12974](https://fragment.com/gift/voodoodoll-12974) |
| Контраст | Signet Ring | Tony Stark / Moonstone | 150 | 11500 | [signetring-429](https://fragment.com/gift/signetring-429) |
| Контраст | Bling Binky | Night Bat / Cyberpunk | 210 | 16100 | [blingbinky-1284](https://fragment.com/gift/blingbinky-1284) |
| Монохром | Desk Calendar | Groundhog Day / Ivory White | 25 | 1920 | [deskcalendar-163494](https://fragment.com/gift/deskcalendar-163494) |
| Монохром | Star Notepad | Negative / Ivory White | 27 | 2070 | [starnotepad-51679](https://fragment.com/gift/starnotepad-51679) |
| Монохром | Ginger Cookie | Opposite / Ivory White | 28 | 2150 | [gingercookie-149389](https://fragment.com/gift/gingercookie-149389) |
| Монохром | Swag Bag | Darkness / Ivory White | 75 | 5750 | [swagbag-46673](https://fragment.com/gift/swagbag-46673) |
| Монохром | Candy Cane | Negativus / Black | 131 | 10040 | [candycane-191380](https://fragment.com/gift/candycane-191380) |
| Монохром | Liberty Figure | Diamond / Black | 140 | 10730 | [libertyfigure-141968](https://fragment.com/gift/libertyfigure-141968) |
| Монохром | Jester Hat | Sketchy / Black | 199 | 15250 | [jesterhat-143381](https://fragment.com/gift/jesterhat-143381) |
| Монохром | Winter Wreath | Old Movie / Black | 250 | 19160 | [winterwreath-8639](https://fragment.com/gift/winterwreath-8639) |
