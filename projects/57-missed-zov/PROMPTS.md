# «Зов» — Мисед против армии фейков

Промпты для генерации кадров и видео. Музыка: TheFatRat — The Calling (108 BPM).
Промпты на английском, потому что генераторы лучше понимают английский. Пояснения на русском.

## Как пользоваться

1. Каждый раз прикладывайте к промпту картинку `0_missed_reference.jpg`, а когда будет готов лист
   персонажа, прикладывайте его вместо неё. Без референса Мисед получится каждый раз разным.
2. В кадрах с оружием прикладывайте ещё и картинку нужного подарка (`1_…5_….png`).
3. В конец каждого промпта картинки добавляйте блок **STYLE** (2D) или **STYLE 3D**.
4. Формат всех кадров 9:16, вертикальный.

---

## Общие блоки

**MISSED (описание персонажа, вставлять везде, где он есть):**
```
Missed: a small bald humanoid creature with a large smooth egg-shaped head, pale peach-pink skin,
huge fully black glossy eyes with no whites, long pointed elf ears sticking straight out sideways,
tiny nose, small sly closed-mouth smile, very thin long neck, skinny doll-like body.
Same face and proportions in every shot. He stays thin and calm, never muscular.
```

**STYLE (2D-аниме):**
```
gritty 90s fighting-manga anime style, heavy black ink hatching and cross-hatching, dramatic
chiaroscuro lighting, intense shadows on faces, speed lines, dust and debris, cinematic low angle,
high contrast, vertical 9:16, ultra detailed, epic atmosphere
```

**STYLE 3D:**
```
cinematic 3D animation, stylized realistic render, volumetric light, dramatic rim lighting,
particles and debris, depth of field, epic scale, vertical 9:16, 4K
```

**ARENA (главная локация):**
```
an underground fighting arena inside a messenger app: the ring floor is built from giant glossy
chat message bubbles, huge notification icons hang above like stadium spotlights, falling spam
messages drift down like ash, crowded dark stands full of anxious spectators, smoke and blue-violet
glow
```

---

## 1. Лист персонажа (сделать первым)

```
Character reference sheet of MISSED. Front view, side view, back view, 3/4 view, close-up of the
face, close-up of the eyes. Second row: the same character in battle mode with a glowing white-blue
aura, heavy ink shadows on the face, a cold focused stare, body still thin. Neutral grey background,
labeled poses. + STYLE
```

---

## 2. Оружие — подарки Telegram

Их пять. Оружие усиливается от сцены к сцене, и каждое достаётся в свой момент. Подарок рисовать
**как на картинке-референсе**, только крупнее и с боевым свечением.

| № | Подарок | Как работает | Против кого |
|---|---|---|---|
| 1 | **Light Sword** | световой меч: одним взмахом прорезает рой | рой мини-фейков |
| 2 | **Hypno Lollipop** | гипнотическая спираль: фейки замирают и начинают бить друг друга | «специалисты» |
| 3 | **Electric Skull** | череп над плечом бьёт молниями по всей толпе | пробуждение, выход из окружения |
| 4 | **Voodoo Doll** | кукла с лицом босса: укол иглой, и гигант корчится | босс |
| 5 | **Mighty Arm** | золотая мускулистая рука надевается на его тонкую руку, финальный удар | добивание босса |

Запасные, если какое-то не понравится: **Stellar Rocket** (влететь на арену верхом на ракете),
**Artisan Brick** (смешной бросок кирпичом), **Astral Shard** (кристаллы как сюрикены),
**Heroic Helmet** (шлем-броня), **Magic Potion** (зелье-усиление).

**Промпты кадров с оружием:**

1. Light Sword:
```
MISSED holds a glowing blue lightsaber with a chrome hilt (exactly like the attached gift image),
one horizontal slash cuts through a swarm of tiny clone creatures, the blade leaves a bright arc
trail, clones burst into floating chat-message fragments. In the ARENA. + STYLE
```
2. Hypno Lollipop:
```
MISSED raises a giant swirling orange-brown hypno lollipop (exactly like the attached gift image),
a hypnotic spiral wave spreads across the ring, surrounding clone creatures freeze with spiral eyes
and start punching each other. In the ARENA. + STYLE
```
3. Electric Skull:
```
A translucent purple glowing skull with a golden crown-crack floats above MISSED's shoulder
(exactly like the attached gift image), lightning bolts shoot from its eye sockets into the crowd
of clones surrounding him, white-blue aura explodes around MISSED, clones fly backward. + STYLE
```
4. Voodoo Doll:
```
MISSED calmly holds a small stitched brown voodoo doll with a red pin (exactly like the attached
gift image), the doll wears a tiny crown like the giant boss, he pushes the pin in, in the
background the towering muscular boss bends over in pain, cracks run across the ring. + STYLE
```
5. Mighty Arm:
```
A huge golden muscular arm (exactly like the attached gift image, golden statue texture) forms
around MISSED's skinny arm, he winds up for a final punch, golden energy and debris swirl around
him, extreme low angle, the giant boss looms above. + STYLE
```

---

## 3. Двойники (60 штук)

**Базовый промпт.** В него подставляется одна строка из списка ниже:
```
Full-body portrait of a FAKE clone of MISSED (same face, same bald head, same black eyes, same
sideways elf ears) but with this change: [ИЗМЕНЕНИЕ]. Smug or shifty expression, standing in the
ARENA, facing the camera, character intro card composition. + STYLE
```
Для «представления бойца» в монтаже сверху накладываем надпись вида «Фейк №47 · Улучшатель».

**Ошибки копии**
1. low-resolution pixelated body, blurry jpeg artifacts
2. a fake checkmark badly drawn with a blue marker on his forehead
3. mismatched eyes, one huge and one tiny
4. one ear pointing up and the other pointing down
5. green skin, like a color copy error
6. ears sticking upward like a rabbit
7. glitching body with visible RGB split and scanlines
8. drawn in crayon like a child's sketch
9. stretched vertically like a wrongly resized image
10. upside-down face
11. three ears
12. head too small for the body

**Ники с ошибкой** (ник напечатан на одежде)
13. a cap with the text "Mlssed"
14. a T-shirt with the text "Misseed"
15. a hoodie with the text "Mised_official"
16. a sports jersey with the text "Missed_Support"
17. a name tag with the text "Real Missed 100%"
18. a sash with the text "Missed2"
19. a baseball jacket with the text "M1ssed"
20. a cape with the text "MissedGifts"

**Схемы скама**
21. a hard hat and a huge wrench, shouting "I'll upgrade your gift!"
22. a fishing rod with a glowing link hook
23. a "Telegram Support" badge and a necktie
24. a giant QR code tattooed on his forehead
25. a Santa suit carrying a sack of stolen gifts
26. holding a sign "send 100 stars"
27. a fake lottery wheel in his hands
28. a fake contract scroll "sign here"
29. a megaphone shouting "free NFT"
30. a fake gift box with a trap inside
31. a crystal ball labeled "guaranteed profit"
32. a stack of fake screenshots in his hands
33. a fake banker visor and an abacus
34. a doctor coat and a stethoscope "account check-up"
35. a piggy bank with a slot labeled "seed phrase"

**Крутые с виду**
36. laser eyes and a thick gold chain
37. sunglasses and a gold grill
38. a samurai topknot and a wooden sword
39. a biker leather jacket and spikes
40. a pirate eye patch and a hook hand
41. a cowboy hat and twin water pistols
42. a ninja mask with only the black eyes visible
43. a ski mask like a robber
44. a boxing robe and red gloves
45. a cyber visor and neon tubes on the body
46. a medieval knight helmet made of cardboard
47. a Viking helmet and a plastic axe
48. a wrestling champion belt made of tinfoil
49. a fur coat and many rings
50. a top hat and a monocle, like a fake millionaire

**Абсурдные**
51. a tiny body and a gigantic head
52. hyper-muscular body with the original tiny face (mini-boss)
53. made of melted wax, dripping
54. inflatable like a pool toy
55. made of chat stickers glued together
56. a body made of spam emails
57. a cardboard cutout held by someone behind
58. a clone riding another smaller clone
59. a swarm of 30 palm-sized clones running like ants
60. a shadow silhouette with glowing fake checkmark eyes

**Групповой кадр армии:**
```
Hundreds of FAKE clones of MISSED filling the entire ARENA and stands, all different (caps, chains,
pixelated, wrong ears, scam signs), all staring at the single real MISSED standing alone in the
center of the ring, top-down epic wide shot. + STYLE
```

---

## 4. Босс — «Король фейков»

```
"King of Fakes": a colossal hyper-muscular giant with the face of MISSED (same bald egg head, black
eyes, sideways elf ears) on a monstrous bodybuilder body with veins and extreme muscle definition,
a crown made of stolen Telegram gifts, a long cape sewn from scam chat messages, a giant fake blue
checkmark emblem glowing on his chest, towering over the ARENA, tiny MISSED in the foreground
seen from behind. + STYLE 3D
```

---

## 5. 2D-ключевые кадры по сюжету

1. **Комната:**
```
MISSED sits on a couch in a dark room at night, his face lit only by a phone screen, notification
bubbles pile up in the air around him with texts like "Missed, your double scammed me",
"Missed, a fake stole my gift". Tired expression. + STYLE
```
2. **Вздох:**
```
Close-up of MISSED, eyes half closed, a long tired sigh, a small cloud of breath, heavy ink
shadows, the glow of the phone below. + STYLE
```
3. **Втягивание:**
```
The phone screen cracks and bursts into pixels, MISSED is pulled into the screen in a spiral of
light and chat bubbles, dynamic perspective, motion blur. + STYLE
```
4. **Выход:**
```
MISSED walks slowly into the ARENA ring, his silhouette backlit by spotlights, hundreds of clones
around the ring, the crowd in the stands frozen in silence. + STYLE
```
5. **Окружили:**
```
The lights go dark, only MISSED's black eyes reflect the light, dozens of fake clones close in on
him from all sides, the spectators cover their mouths in fear. + STYLE
```
6. **Пробуждение:**
```
Extreme close-up of MISSED's black eye, a reflection of lightning inside, then a white-blue aura
erupts, his ears glow, debris rises from the floor. + STYLE
```
7. **Возвращение подарков:**
```
Hundreds of colorful gifts burst out of defeated clones and fly in glowing arcs toward the cheering
spectators in the stands, confetti of chat bubbles, triumphant mood. + STYLE
```
8. **Финал:**
```
MISSED back on the couch in the dark room, satisfied smile, the phone buzzes again with a new
message "Missed, there's another one...", he rolls his eyes. + STYLE
```

---

## 6. 3D-сцены (Gemini / Veo, видео)

Прикладывайте лист персонажа и кадр босса. Длина каждой сцены 5–8 секунд, потом режем под бит.

1. **Облёт при выходе:**
```
Cinematic 3D: the camera orbits 360 degrees around small calm MISSED standing in the center of the
ARENA, hundreds of fake clones around the ring, spotlights sweep, spam ash falling, slow and epic.
+ STYLE 3D
```
2. **Появление босса:**
```
Cinematic 3D: the ring cracks, the giant King of Fakes rises from the floor, his shadow covers the
arena, camera tilts up from tiny MISSED to the boss's face, crown of stolen gifts glinting.
+ STYLE 3D
```
3. **Удар босса:**
```
Cinematic 3D: the King of Fakes slams his giant fist down, MISSED leaps aside at the last moment,
the ring explodes into flying chat bubbles, slow motion, camera shake. + STYLE 3D
```
4. **Вуду:**
```
Cinematic 3D: close-up of MISSED pushing a red pin into a small voodoo doll, cut to the giant boss
bending in pain, his fake checkmark emblem cracking. + STYLE 3D
```
5. **Финальный удар (главная сцена):**
```
Cinematic 3D slow motion: MISSED jumps up with a giant golden muscular arm, punches straight into
the glowing fake checkmark on the boss's chest, freeze moment, then the checkmark shatters, the
giant boss disintegrates into thousands of chat messages, camera orbits 360 degrees around the
impact. + STYLE 3D
```
6. **Разлёт подарков:**
```
Cinematic 3D: thousands of gifts fly out of the collapsing boss in glowing streams toward the
stands, the crowd cheers, MISSED stands alone in the light, camera pulls back to a wide shot.
+ STYLE 3D
```

---

## 7. Оживление 2D-кадров (image-to-video)

Чтобы не вышло слайд-шоу, каждый 2D-кадр оживляем коротким движением (3–5 секунд):
```
Animate this anime frame: [действие], speed lines, camera push-in, debris and dust particles moving,
impact flash, keep the character's face and proportions unchanged.
```
Действия: «sword slash and clones bursting», «hypnotic spiral spreading», «lightning strikes»,
«aura exploding», «slow walk forward», «clones closing in».

## Монтаж

- Импакт-кадр (1–2 кадра, инверсия в чёрно-белое) на каждый сильный удар музыки.
- В затишьях медленные проезды камеры, в дропах смена кадра на каждый удар.
- Пятерых-шестерых двойников подаём стоп-кадром с надписью «Фейк №…», остальных мелькаем пачкой.
- Последняя надпись: «Настоящий Мисед ничего не просит».
