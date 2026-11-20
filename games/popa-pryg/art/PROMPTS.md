# Попа-Прыг: промпты для картинок и видео

Как пользоваться: промпты на английском (генераторы понимают их лучше). Везде, где есть персонаж-попа,
прикладывайте **референс** — самую первую картинку попы (фиолетовые шорты, белые носки, красные кеды,
зелёный фон) и скриншот игры (`art/poster.jpg`). Готовые файлы присылайте в чат, я встрою их в игру.

## Общий стиль (добавлять в конец каждого промпта)

```
cute stylized 3D render, soft glossy plastic toy look, rounded shapes, Pixar-like lighting,
bright saturated pastel colors, clean sky-blue background, soft shadows, high detail, no text
```
Негатив (если генератор умеет): `text, letters, watermark, realistic human, nudity, gore, dark, blurry, deformed`.

Главная героиня: «cartoon butt character: two round cheeks in bright purple shorts with a thick purple waistband,
short peach-skin legs, white socks, red sneakers with white soles, no upper body».

---

## 1. Картинки для меню и бота

| # | Что | Размер | Где в игре |
|---|---|---|---|
| 1 | Фон меню | 1080×1920, JPG | позади меню вместо 3D-сцены на старте |
| 2 | Логотип без текста (плашка под название) | 1024×512, PNG с прозрачностью | над меню; буквы «Попа-Прыг» я наложу сам, нейросети путают кириллицу |
| 3 | Карточка «Поделиться» | 1280×720, JPG | картинка, которая уходит в чат вместе с результатом |
| 4 | Заставка загрузки | 1080×1920, JPG | пока игра грузится |

1. **Фон меню**
   `vertical 9:16 scene: endless path of colorful round cylinders (yellow, pink, cyan, purple, green) floating in a bright blue sky with fluffy clouds, the cartoon butt character mid-jump above a cylinder in the lower third, soft countryside fields far below in haze, empty space in the upper half for a menu`
2. **Плашка логотипа**
   `wide glossy bubble-shaped banner, purple and hot pink candy plastic, thick rounded outline, small cartoon butt character peeking from the right edge, sparkles, transparent background, centered, no text`
3. **Карточка «Поделиться»**
   `horizontal 16:9 celebration scene: the cartoon butt character jumping triumphantly over colorful cylinders, confetti, golden glow, bright sky, empty dark-purple rounded panel on the left third for a score number`
4. **Заставка загрузки**
   `vertical 9:16: the cartoon butt character stretching before a jump on a single yellow cylinder, sunrise sky, calm and cute, lots of empty space at the bottom for a loading bar`

## 2. Портреты боссов (для карточки босса и подсказок)

1024×1024, PNG с прозрачным фоном, персонаж по центру, по пояс или целиком, смотрит в камеру, «злой, но милый».

1. Дракон Жарыч — `chubby green cartoon dragon with orange bat wings, cream horns, yellow belly, grumpy eyebrows, puffing a small fireball`
2. Снеговик-громила — `big angry snowman with coal eyes, carrot nose, black top hat with red band, red scarf, stick arms holding a snowball, sitting on a cloud`
3. Кактус-ковбой — `green cactus cowboy with a brown cowboy hat, black mustache, white spikes, arms raised, in a terracotta pot on a cloud`
4. Робот-громобой — `chunky grey robot with a glowing red visor, antenna with red bulb, cyan chest light, small rocket flames under it`
5. Пчелиная королева — `round yellow-black queen bee with a tiny golden crown, big shiny eyes, translucent wings, stinger`
6. Краб-пират — `red cartoon crab with a black pirate hat with skull, eye patch, huge claws, holding a wooden barrel`
7. НЛО — `silver flying saucer with a glass dome, cute green alien with big black eyes inside, colorful rim lights, green tractor beam`
8. Грозовая туча — `dark grey storm cloud with angry eyes and frown, small lightning bolts and rain drops`
9. Гигантский кот — `huge fluffy orange tabby cat head and paws, green slit eyes, mischievous grin, paw raised to swat`
10. Тёмная Попа — `evil twin of the butt character: dark purple-black shorts, glowing red eyes on the cheeks, dark red sneakers, purple smoky aura`

Финальный персонаж (хозяин попы), 2 картинки 1024×1024 PNG:
- плачет: `cute cartoon boy upper body only (no legs, no hips), cyan t-shirt with yellow diamond, brown hair tuft, big teary eyes, crying, sitting on a golden platform with harps`
- счастлив: то же, но `laughing happily, hugging the cartoon butt character`

## 3. Значки особых цилиндров (для подсказок)

512×512, PNG с прозрачностью, вид сверху-сбоку, один цилиндр по центру.
Шаблон: `single round cylinder platform, 3/4 top view, game icon, [описание], transparent background`

| Цилиндр | [описание] |
|---|---|
| Батут | `red with white stripes, black trampoline net on top` |
| Пушка | `black iron, cannon mouth on top with smoking fuse` |
| Портал | `dark purple, swirling glowing violet vortex on top` |
| Ездящий | `steel, on a metal rail, yellow arrows left and right` |
| Призрак | `translucent pale blue, cute ghost face, faint glow` |
| Лёд | `icy light blue, snow on top, icicles hanging` |
| Ветер | `grey with fan grille on top, white wind arrow above` |
| Желе | `wobbly translucent green jelly` |
| Копилка | `golden, pink piggy bank standing on top, coins` |
| Диско | `black with rainbow tiles, mirror disco ball on top` |
| Полукактус | `sandy, half of the top covered with green cactus spikes` |
| Обменник | `half purple half orange, two cyan circular arrows on top` |
| Секретный | `rainbow colored with a big white question mark floating above` |

## 4. Текстуры (бесшовные)

Важно: **бесшовные** (`seamless tileable texture`), без теней и перспективы, вид строго сверху или в лоб.

**Бока площадок боссов**, 2048×512 (бесшовные по горизонтали), и **верх площадок**, 1024×1024 (круг вписан в квадрат):

| Босс | Бок | Верх |
|---|---|---|
| Дракон | `dark volcanic basalt with glowing orange lava cracks` | `round lava rock top, cracks radiating from a glowing center` |
| Снеговик | `packed snow and blue ice with snowflakes, snow cap along the top edge` | `fresh snow surface with sparkles` |
| Кактус | `desert sand with terracotta and turquoise western zigzag band` | `sand dunes ripples with small pebbles` |
| Робот | `steel plates with rivets, yellow-black hazard stripes at top` | `diamond tread metal plate with circular lines` |
| Пчёлы | `golden honeycomb with honey dripping from the top` | `honeycomb hexagons, some filled with honey` |
| Краб | `vertical wooden ship planks with nails` | `wooden deck planks with a big red X` |
| НЛО | `dark navy sci-fi panel with neon green alien glyphs` | `landing pad with concentric neon rings and glyphs` |
| Туча | `dark storm stone with yellow lightning bolts` | `grey swirling cloud stone` |
| Кот | `pink yarn wrapped around, soft wool texture` | `pink felt with paw prints` |
| Тёмная Попа | `black stone with glowing red cracks and purple runes` | `black stone, red glowing rings, runes around the edge` |

Ещё две:
- **Земля внизу**, 1024×1024: `seamless top-down aerial patchwork of soft green and wheat farm fields with hedges, tiny ponds, stylized, muted pastel`
- **Небо**, 2048×1024: `seamless panoramic bright cartoon sky gradient with soft fluffy clouds`

## 5. Видео

1. **Трейлер, 15–20 с, 9:16** (канал, реклама, описание бота). Сцены по 2–3 с:
   1) `the cartoon butt character bounces on colorful cylinders in the sky, camera follows from behind, fast and cheerful`
   2) `a chubby green dragon flies in and shoots fireballs, the butt dodges left and right`
   3) `the butt lands on a rainbow cylinder with a question mark, confetti explodes`
   4) `two butts, purple and orange shorts, jump side by side on parallel paths, one throws a cartoon poop at the other, it splats harmlessly`
   5) `golden road of cylinders leading to a golden platform with arches and harps, a crying cartoon boy smiles as the butt jumps into his arms, they dance`
   6) финальный кадр — плашка логотипа, текст «Попа-Прыг» я добавлю сам.
2. **Приветствие для /start, 5–8 с, 9:16, бесшовный цикл**: `the cartoon butt character bounces in place on a yellow cylinder, waves its sneakers, clouds drift behind, seamless loop`. Бот будет присылать его вместо постера.
3. **Короткие заставки боссов, 3 с, 1:1** (по желанию): `[описание босса из раздела 2] appears dramatically with a puff of smoke, roars at the camera, game boss intro`. Покажу их на карточке перед боем.

## Что прислать в первую очередь

1. Портреты 10 боссов. С ними сразу будет карточка босса перед боем.
2. Значки особых цилиндров. Ими можно украсить подсказки.
3. Видео-приветствие для /start.
4. Остальное по желанию.

---

# Интерфейс

Текст на кнопках и сами кнопки я оставляю в коде: так они чёткие на любом экране и надписи не ломаются.
От картинок нужны **значки, медали, иллюстрации для экранов и фоны**: их я ставлю рядом с текстом.

**Референсы:** `art/ui-reference.png` (как интерфейс выглядит сейчас), `art/hero-reference.jpg` (героиня).
Сделай первый значок, и если он нравится, прикладывай его как референс ко всем остальным: так набор будет единым.

**Палитра игры** (вставлять в промпты как есть): purple `#a43cff`, red `#ff3b2f`, yellow `#ffd60a`,
sky blue `#3aa8ff`, orange `#ff8a1a`, deep ink outline `#2a1457`, white.

**Добавлять в конец каждого промпта интерфейса:**
```
glossy candy 3D mobile game icon, chunky rounded shapes, soft bevel and top highlight,
thick deep-purple (#2a1457) outline, palette: purple #a43cff, red #ff3b2f, yellow #ffd60a,
sky blue #3aa8ff, orange #ff8a1a, white; centered, transparent background, no text, no letters
```

## А. Значки меню и игры (512×512, PNG без фона)

| # | Значок | Промпт (вставить перед общим окончанием) |
|---|---|---|
| 1 | Играть | `big yellow play triangle with a tiny purple cartoon butt bouncing on it` |
| 2 | Профиль | `round avatar badge with a purple-shorts cartoon butt silhouette inside` |
| 3 | Друзья | `two cartoon butts side by side, one in purple shorts, one in orange shorts, high-fiving with sneakers` |
| 4 | Лидерборд | `golden trophy cup with a star, small purple ribbon` |
| 5 | Магазин (на потом) | `cute shop stall with striped red-white awning and a shopping bag` |
| 6 | Настройки | `chunky purple gear cog` |
| 7 | Пауза | `two thick rounded white pause bars on a purple circle` |
| 8 | Звук включён | `yellow speaker with sound waves` |
| 9 | Звук выключен | `grey speaker with a small red cross` |
| 10 | Микрофон включён | `green microphone with sound waves` |
| 11 | Микрофон выключен | `grey microphone with a red slash` |
| 12 | Автопилот | `cute robot head steering a small ship wheel` |
| 13 | Какашка | `cute smiling cartoon poop swirl with big eyes, brown and glossy` |
| 14 | Реакции | `round yellow laughing face with tears of joy` |
| 15 | Поделиться | `paper plane flying out of a purple circle with sparkles` |
| 16 | Назад | `thick rounded arrow pointing left, purple` |
| 17 | Сюжет | `open storybook with a golden star bookmark` |
| 18 | Бесконечный | `glossy purple infinity sign made of cylinders` |
| 19 | Испытание дня | `calendar page with a golden star and a small flame` |
| 20 | Онлайн: случайный | `pink dice showing a butt on one face` |
| 21 | Онлайн: с другом | `two sneakers, red and blue, touching toes, small heart above` |
| 22 | Копировать | `two overlapping rounded white cards` |
| 23 | Принять | `thick green check mark` |
| 24 | Отклонить | `thick red cross` |

## Б. Медали лидерборда (512×512, PNG без фона)

- `gold medal with number 1 shape embossed as a star, red ribbon` — 1 место
- `silver medal with a star, blue ribbon` — 2 место
- `bronze medal with a star, green ribbon` — 3 место
- `small golden crown with three round gems` — над аватаркой лидера

## В. Иллюстрации для экранов (1024×1024, PNG без фона, героиня в центре)

| Экран | Промпт |
|---|---|
| Проигрыш | `the cartoon butt character sitting dizzy on a cylinder, cartoon stars and birds circling above` |
| Новый рекорд | `the cartoon butt character jumping with a gold medal, confetti burst` |
| Пауза | `the cartoon butt character asleep lying on a cylinder, big Zzz bubbles, tiny pillow` |
| Ждём соперника | `the cartoon butt character looking through binoculars, standing on a cylinder` |
| Нет друзей | `lonely cartoon butt character holding a big magnifying glass, searching` |
| Пустой лидерборд | `empty three-step winners podium with a question mark, confetti on the floor` |
| Как тебя зовут | `the cartoon butt character holding a blank white name tag sign` |
| Победа над боссом | `the cartoon butt character standing proudly on top of a golden trophy, flexing` |
| Сюжет пройден | `the cartoon butt character and a cartoon boy in a cyan t-shirt dancing together, hearts around` |

## Г. Фоны

- **Фон меню**, 1080×1920 — промпт из раздела «Картинки для меню и бота» выше.
- **Узор для окон**, 512×512, бесшовный: `seamless subtle pattern of tiny lavender cylinders, stars and little sneakers on very light lavender #f6f1ff, low contrast, flat`
- **Шапка окна**, 1080×300: `wide soft gradient banner from purple #a43cff to pink, small clouds and floating cylinders, flat cartoon, no text`

## Что в первую очередь

1. Значки 1–4 и 6 (главное меню) и 17–21 (выбор режима).
2. Иллюстрации «Проигрыш», «Новый рекорд», «Пауза», «Ждём соперника».
3. Медали.
4. Остальное.
