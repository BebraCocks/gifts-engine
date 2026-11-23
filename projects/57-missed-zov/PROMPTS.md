# «Зов» — Мисед против армии фейков

Промпты для генерации кадров и видео. Музыка: TheFatRat — The Calling (108 BPM).
Промпты на английском, потому что генераторы лучше понимают английский. Пояснения на русском.

## Как пользоваться

1. Каждый раз прикладывайте к промпту лист персонажа `refs/missed_sheet.png` (готов 2026-11-23). Без референса Мисед получится каждый раз разным.
2. В кадрах с оружием прикладывайте ещё и картинку нужного подарка (`1_…5_….png`).
3. В конец каждого промпта картинки добавляйте блок **STYLE** (2D) или **STYLE 3D**.
4. Формат всех кадров 9:16, вертикальный.

---

## НОВОЕ НАПРАВЛЕНИЕ (решение автора, 2026-11-23): весь ролик в 3D

Идея упрощается: почти все сцены делаем в 3D (Gemini/Veo), музыку автор подберёт новую.
Начало: Мисед лежит на кровати, телефон на тумбочке. 1,5–2 секунды ничего не происходит,
потом экран загорается, Мисед садится, берёт телефон и смотрит в него. Над ним на секунду
всплывают и исчезают надписи-сообщения, каждое озвучено своим голосом Fish Audio
(озвучка готова: `build/voice/msg_01…08.mp3`, голоса — в `docs` ниже). Мисед молчит.

Голоса сообщений (Fish Audio, модель drama-3):
- «Девушка» `0786b17418a146dfa037e87e5f112953` — сообщения 1 и 7;
- «Дерзкий Парень» `6ada82e315e648b6a30a2e2210844cbf` — 2 и 8;
- «Подросток» `47eabb7c72f247758b9d55fa4eeede28` — 3;
- «Девушка» `7ac07cd587b2454090ae01f3ab9f0fd4` — 4;
- «Энергичный подросток» `9bbc7f0a18ba45bc8058ef56638ec030` — 5;
- «Adam» `4177b0a68e4e46879c8e228ae388934f` — 6.

### Сюжет 3D-версии (автор, 2026-11-23), 60–130 секунд под новую музыку автора

1. Спальня, не дольше 8–10 секунд: Мисед спит, телефон загорается, он садится и смотрит в телефон.
   Над ним по очереди всплывают три сообщения от трёх обманутых людей, каждое своим голосом.
2. Мисида затягивает в телефон, он попадает на арену. На арене три фейка, на трибуне три жертвы.
3. Мисед побеждает первого фейка и возвращает украденный подарок первой жертве. Так со всеми тремя.

Готово: `refs/frames/3d_01_bedroom.jpg` (9/10).

### 3D-промпты начала

**3D-1. Лист персонажа в 3D** (приложить `refs/missed_sheet.png`)
```
Use the attached character sheet as the exact reference. Turn this character into a high-quality stylized 3D animated movie character, like a modern 3D animation feature: Missed, a cartoon alien mascot with a large smooth bald egg-shaped head, pale peach-pink skin with soft subsurface scattering, huge glossy black eyes with reflections, long pointed ears sticking straight out sideways, tiny nose, small sly closed-mouth smile, long slim neck, black oversized hoodie with soft fabric folds, black cargo pants, white sneakers. Character turnaround: front, 3/4, side and back views, full body, plus a face close-up. Neutral light grey studio background, soft studio lighting, clean 3D render, vertical 9:16.
```

**3D-2. Первый кадр: спальня** (приложить готовый 3D-лист персонажа)
```
Use the attached 3D character sheet as the exact reference for Missed. Cinematic 3D animated movie still: a cozy dark bedroom at night, Missed lies on his back on a bed under a blanket, eyes closed, calm. On the bedside table next to him lies a smartphone with a dark screen. Soft blue moonlight from the window, deep shadows, quiet atmosphere. Medium-wide shot from the side, the bed and the bedside table both clearly visible. Stylized high-quality 3D render, volumetric light, shallow depth of field, vertical 9:16.
```

**3D-3. Видео начала** (Veo, image-to-video из кадра 3D-2)
```
Animate this 3D scene. For the first two seconds nothing moves, the room is quiet. Then the smartphone on the bedside table lights up and vibrates, its cold blue glow fills the room. Missed opens his eyes, slowly sits up in bed, reaches over, picks up the phone and looks at the screen with a calm, unbothered face, mouth closed. Slow subtle camera push-in. Keep the character exactly as in the reference. Audio: quiet room tone, then phone vibration buzz. No dialogue, no music, Missed makes no sound.
```

## Стиль: оживлённая цветная манга (решение автора, 2026-11-23)

Не чёрно-белая манга и не плавное аниме, а **цветная манга, которую оживили** (motion manga):
- рисунок как в цветной манге: жирный чёрный контур, штриховка, растровые точки, яркие цвета;
- часть кадров — страницы с 2–3 панелями, панели появляются по одной под бит;
- движение как в примере автора: кадр почти неподвижен, двигаются голова, глаза, дыхание, аура,
  медленный наезд; в экшене одно резкое движение и пауза; кадр держится 3–5 секунд, жёсткие склейки;
- звукоподражания крупными русскими буквами («БАМ!», «ХИ-ХИ», «ВЖУХ») добавляем в монтаже.

Первые три кадра (`refs/frames/`) уже в этом стиле, оценки 9, 9.5, 9.

## Общие блоки

**MISSED (описание персонажа, вставлять везде, где он есть):**
```
Missed: an original stylized cartoon alien mascot with a large smooth egg-shaped head, pale peach-pink skin,
huge fully black glossy eyes with no whites, long pointed elf ears sticking straight out sideways,
tiny nose, small sly closed-mouth smile, long slim neck. He wears a black oversized hoodie with the
hood down, black cargo pants and white sneakers.
Same face and proportions in every shot. He stays thin and calm, never muscular.
He is completely silent: mouth always closed, never talks, never shouts. Cool, cold, unbothered,
a quiet heavy aura around him.
```

**STYLE (2D-аниме):**
```
full-color manga style, like a colored manga page brought to life: bold black ink outlines, ink hatching and screentone dot shading, vivid colors, dramatic lighting, high contrast, speed lines, highly detailed, vertical 9:16
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

## 3. Двойники: 20 листов по 3 фейка

**Чёрное худи и персиковая кожа только у настоящего Миседа.** У каждого фейка свой цвет кожи, своя одежда
и свой цвет одежды под его «тему»,
поэтому их видно издалека, и настоящий выделяется в толпе. Лицо у всех как у Миседа, телосложение в
основном тоже, отличаются рост и ширина, у четверых третья рука или нога.
Каждый раз прикладывайте лист персонажа `refs/missed_sheet.png`. Готовый лист режем на три кадра.
Листы 1–3 сделаны на фоне арены (оценки 9, 8, 9), листы 4–6 на однотонном (8, 9, 8.5), листы 7–9 (9, 8.5, 9), листы 10–12 (9, 9.5, 9), листы 13 и 15 (9, 9.5), лист 14 на переделку (7.5: настоящие револьверы, четыре ноги),
листы 16–18 (9, 9.5, 9), листы 19–20 (9.5, 9).
Ничего не висит над фейками: все отличия на теле, на одежде или в руках, у многих в руках оружие.
 С листа 4 фон однотонный, цвета, которого нет
на фейках этого листа, чтобы их было легко вырезать.

**Лист 1**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: light blue skin, a low-resolution pixelated copy with glitchy jpeg artifacts, wearing a bright green tracksuit, slightly taller than Missed.
Center: lime green skin, a fake blue checkmark badly drawn with a marker on his forehead, wearing a plain white T-shirt and blue jeans, a bit shorter.
Right: lavender purple skin, mismatched eyes, one huge and one tiny, wearing a red flannel shirt and khaki shorts, wider shoulders.
Blurred background: an underground fighting arena built from giant chat message bubbles, notification icons as spotlights, dark smoky stands.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 2**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: deep red skin, one ear pointing up and the other down, wearing a yellow raincoat and rubber boots, even skinnier.
Center: green skin like a color copy error, wearing an orange jumpsuit.
Right: bubblegum pink skin, ears sticking upward like a rabbit, wearing pink pajamas and bunny slippers, a little chubby belly.
Blurred background: an underground fighting arena built from giant chat message bubbles, notification icons as spotlights, dark smoky stands.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 3**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: teal skin, a glitching body with RGB split and scanlines, wearing a purple windbreaker, tall and lanky.
Center: drawn in crayon like a child's sketch, wearing a striped kids' sweater, short and stocky.
Right: cool grey skin, stretched vertically like a wrongly resized image, wearing a grey business suit.
Blurred background: an underground fighting arena built from giant chat message bubbles, notification icons as spotlights, dark smoky stands.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 4**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: coral red skin, an upside-down face, wearing a Hawaiian shirt and sandals.
Center: sky blue skin, three ears, wearing a denim jacket and jeans, hunched posture.
Right: olive green skin, a head too small for the body, wearing a gym tank top and joggers.
Background: a perfectly flat solid chroma key magenta #FF00FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 5**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: turquoise skin, a red cap with the text "Mlssed" and a red varsity jacket, slightly taller.
Center: magenta skin, a white T-shirt with a cheap print "Misseed" and ripped skinny jeans, a bit shorter.
Right: pale violet skin, a neon green hoodie with the text "Mised_official".
Background: a perfectly flat solid neutral mid-grey #808080 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 6**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: tomato red skin, a blue sports jersey with the text "Missed_Support" and shorts, wider shoulders.
Center: aqua cyan skin, an office shirt with a name tag "Real Missed 100%", three arms.
Right: golden yellow skin, a sash "Missed2" over a cheap shiny tuxedo.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 7**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: indigo blue skin, a yellow-and-blue baseball jacket with the text "M1ssed".
Center: peach orange skin, a cape with the text "MissedGifts" over a cheap superhero spandex suit, a little chubby belly.
Right: emerald green skin, an orange hi-vis vest and a hard hat, the text "I'll upgrade your gift" printed on the vest, gripping a huge wrench like a weapon.
Background: a perfectly flat solid chroma key magenta #FF00FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 8**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: rose pink skin, fishing waders and a bucket hat, holding a fishing rod like a spear with a glowing link-shaped hook, three legs.
Center: steel blue skin, a white shirt, blue tie, headset and a badge "Telegram Support" on the chest, holding a stun baton.
Right: lemon yellow skin, a QR code tattooed on his forehead, wearing a grey tech-bro zip vest.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 9**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: crimson red skin, a red Santa suit, a sack of stolen gifts on his back, swinging a candy cane like a club, short and round.
Center: sand beige skin, a brown poncho with "send 100 stars" printed on it, holding a slingshot.
Right: neon green skin, a sparkly gold game-show host blazer, holding a microphone like a club.
Background: a perfectly flat solid chroma key blue #0000FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 10**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: royal purple skin, a brown lawyer suit and glasses, holding a rolled contract like a baton, a "sign here" badge on the lapel.
Center: hot pink skin, a neon pink tracksuit with "FREE NFT" printed across the chest, holding a megaphone like a hammer.
Right: cobalt blue skin, a red courier uniform, holding a gift box with metal spikes like a weapon.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 11**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: amber orange skin, a purple fortune-teller robe and turban, holding a heavy crystal ball like a mace.
Center: silver grey skin, a white suit and gold sunglasses like a crypto influencer, "PROFIT" written on the tie, three arms.
Right: jade green skin, a green banker vest and visor, holding a big wooden abacus like a shield.
Background: a perfectly flat solid chroma key blue #0000FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 12**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: cherry red skin, a white doctor coat with "account check-up" on the badge, holding a giant syringe.
Center: lilac skin, a beige trench coat and fedora, hugging a piggy bank with "seed phrase" written on it.
Right: chartreuse skin, glowing red eyes, a thick gold chain and a white tracksuit, brass knuckles on both hands.
Background: a perfectly flat solid chroma key blue #0000FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 13**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: navy blue skin, sunglasses, a gold grill and a leopard print jacket.
Center: salmon pink skin, a samurai topknot, a blue kimono and a wooden katana in his hand.
Right: charcoal grey skin, a leather biker jacket with spikes and a red bandana, holding a bike chain.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 14**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: cyan skin, a pirate coat, an eye patch and a hook hand, holding a cutlass, exactly three legs (not four).
Center: mustard yellow skin, a cowboy hat, a brown leather vest, holding two bright orange-and-green plastic toy water pistols (clearly toys, not real guns), bow-legged stance.
Right: plum purple skin, a dark blue ninja outfit and mask, only the black eyes visible, holding nunchucks.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 15**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: brick red skin, a ski mask and a black-and-white striped robber shirt, a loot bag in one hand and a crowbar in the other.
Center: seafoam green skin, a red satin boxing robe and red boxing gloves on his hands.
Right: electric blue skin, a silver cyber jacket, a glowing cyan visor and cyan neon tubes on the body, holding a cyan neon whip.
Background: a perfectly flat solid chroma key magenta #FF00FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 16**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: tangerine skin, knight armor and helmet made of cardboard, holding a cardboard sword and shield.
Center: dusty pink skin, a Viking helmet, a fur vest and a plastic axe in his hand.
Right: moss green skin, a green wrestling singlet and a championship belt made of tinfoil around the waist.
Background: a perfectly flat solid chroma key blue #0000FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 17**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: violet skin, a huge fur coat and rings on every finger, holding a golden cane.
Center: ice blue skin, a purple velvet suit, a top hat and a monocle like a fake millionaire.
Right: apricot skin, a tiny body and a gigantic head, wearing a yellow baby onesie, holding a toy rattle like a mace.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 18**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: forest green skin, a hyper-muscular body with the original small face, a tight white tank top (mini-boss).
Center: made of melted dripping orange wax, wearing a waiter outfit with a bow tie, holding a serving tray like a shield.
Right: denim blue skin, inflatable like a pool toy, wearing yellow palm-tree print swim shorts, holding an orange pool noodle like a sword.
Background: a perfectly flat solid chroma key magenta #FF00FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 19**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: a body made entirely of red, yellow, blue and purple chat stickers glued together (no green stickers).
Center: a body made of crumpled spam emails, wearing an envelope-print shirt.
Right: a flat cardboard cutout of a fake Missed printed in faded cyan and yellow colors, wearing a printed yellow T-shirt, a wooden stand on the back, a little crooked.
Background: a perfectly flat solid chroma key green #00FF00 backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Лист 20**
```
Use the attached character sheet as the reference for the face and head only. Character lineup sheet: three different FAKE copies of the cartoon alien mascot Missed standing side by side on the same ground line, full body, evenly spaced, heights can differ. No floating objects, signs, text or speech bubbles around them; everything that makes each one different is on his body or in his hands. All three keep his face shape (bald egg-shaped head, huge black eyes, long ears sticking out sideways) and mostly his slim build, but each has a different bright skin color (only the real Missed is pale peach-pink). IMPORTANT: none of them wears a black hoodie; each has a completely different outfit and color palette so they are easy to tell apart from far away. Smug, shifty, mocking expressions.
Left: pastel green skin, a jockey outfit and helmet, holding a riding crop.
Center: copper skin, a tiny palm-sized clone in an orange shirt standing on the ground, holding a toothpick like a sword.
Right: a pitch-black shadow silhouette with glowing white fake-checkmark eyes.
Background: a perfectly flat solid chroma key blue #0000FF backdrop filling the whole frame, no arena, no floor, no shadows, no reflections, even lighting, clean sharp edges around the characters for easy cutout.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Групповой кадр армии:**
```
Hundreds of FAKE clones of MISSED filling the entire ARENA and stands, all in different bright
outfits and different bright skin colors (blue, green, purple, yellow, red...), none in a black hoodie, all staring at the single real MISSED standing alone in the
center of the ring, top-down epic wide shot. + STYLE
```

---

## 4. Босс — «Король фейков»

**Идея.** Король собран из всех фейков сразу: кожа сшита лоскутами всех их цветов. Он надел гигантскую
подделку чёрного худи настоящего Миседа, но мышцы её порвали. На груди огромная поддельная галочка,
в неё и придётся финальный удар золотой рукой.

Готово 2026-11-23: `refs/boss_sheet.png` (9.5) и `refs/boss_poster.png` (9).

**4.1. Лист босса** (приложить `refs/missed_sheet.png`):
```
Use the attached character sheet as the reference for the face and head shape. Character design sheet of the final boss "King of Fakes": a colossal hyper-muscular giant version of the cartoon alien mascot Missed, three times taller than him. Same bald egg-shaped head, long ears sticking out sideways and huge glossy black eyes, but the face is twisted into an arrogant, menacing grin with sharp teeth, and each eye has a tiny glowing blue checkmark-shaped pupil. His skin is a patchwork stitched together from many colors (light blue, lime green, purple, red, yellow, pink, teal) with visible stitches, as if made from all the fake clones. He wears a giant cheap knockoff of Missed's black hoodie, torn apart by his muscles, sleeves ripped off, hood hanging in shreds. On his bare chest glows a huge blue fake verification checkmark emblem with a thin crack in it. A heavy crown made of stolen Telegram gifts: gift boxes with ribbons, a plush frog, a golden cap, a crystal, a glowing star, held together with chains. A long tattered cape stitched from chat message bubbles with scam texts "send stars", "I'll upgrade your gift", "free NFT". Huge fists wrapped in chains, black cargo pants, giant torn white sneakers.
Layout: front view full body, back view full body showing the cape, side view, and a large face close-up with the grin and checkmark pupils.
Background: a perfectly flat solid neutral mid-grey #808080, no shadows, clean edges.
90s fighting-manga anime style, extreme muscle definition and veins, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**4.2. Постер-кадр** (приложить лист персонажа Миседа и готовый лист босса):
```
Use the attached images as references: the first for the real Missed (small, calm, black hoodie, pale peach-pink skin), the second for the boss "King of Fakes". Epic key art: the colossal King of Fakes towers over the arena, arms spread wide, crown of stolen gifts glinting, cape of scam chat bubbles flowing, the fake blue checkmark on his chest glowing, his shadow covering the ring. In the foreground, seen from behind, tiny real Missed stands calm and silent, hands in hoodie pocket, a faint white-blue aura around him. Underground fighting arena built from giant chat message bubbles, notification icons as spotlights, crowded dark stands, spam messages falling like ash, cracks in the floor. Extreme low angle, massive scale contrast.
90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

## 5. 2D-ключевые кадры по сюжету

Мисед всю дорогу **молчит**: ни слов, ни криков, рот закрыт. Всё играет взгляд и аура.

1. **Берёт телефон:**
```
Dark room at night, a phone on a table buzzes and lights up with a flood of notifications,
MISSED's thin hand slowly picks it up, his calm face lit from below by the screen. + STYLE
```
2. **Читает (вставка экрана):**
```
Close-up of a phone screen in a dark room, a chat list flooded with messages addressed to Missed:
"Missed, your double scammed me", "Missed, a fake took my gift", "Missed, someone with your name
asked for my stars", "Missed, help". Reflections of the screen in MISSED's black eyes. + STYLE
```
3. **Молчаливый взгляд:**
```
Extreme close-up of MISSED, completely silent, mouth closed, the glow of the phone below, his black
eyes slowly narrow, heavy ink shadows fall over his face, a faint aura starts to flicker around his
ears. + STYLE
```
4. **Втягивание:**
```
The phone screen cracks and bursts into pixels, MISSED is pulled into the screen in a spiral of
light and chat bubbles, dynamic perspective, motion blur. + STYLE
```
5. **Приземление на арену:**
```
MISSED lands on one knee in the center of a gigantic ARENA, the impact cracks the floor of chat
bubbles and sends up dust, hundreds of fake clones encircle him from every side, they laugh,
giggle and point at him mockingly, extreme wide shot from above, he is a tiny figure in the
center. + STYLE
```
6. **Фейки смеются:**
```
Close-ups of several fake clones of MISSED laughing hysterically: one giggling behind his hand,
one bent over with laughter, one with a wide mocking grin and tears of laughter, distorted
fisheye angles, sweat and spit, heavy ink shadows. + STYLE
```
7. **Атака со всех сторон:**
```
Dozens of fake clones leap at MISSED at once from every direction, frozen mid-air in a dramatic
radial composition, MISSED stands still in the center, silent, eyes calm, a split second before
he strikes. + STYLE
```
8. **Ответный удар:**
```
MISSED moves in a blur, a single strike, the attacking fake clones are blasted outward in a ring
shockwave, speed lines radiating from him, impact flash. + STYLE
```
9. **Окружили:**
```
The lights go dark, only MISSED's black eyes reflect the light, dozens of fake clones close in on
him from all sides, the spectators cover their mouths in fear. + STYLE
```
10. **Пробуждение:**
```
Extreme close-up of MISSED's black eye, a reflection of lightning inside, then a white-blue aura
erupts, his ears glow, debris rises from the floor. + STYLE
```
11. **Возвращение подарков:**
```
Hundreds of colorful gifts burst out of defeated clones and fly in glowing arcs toward the cheering
spectators in the stands, confetti of chat bubbles, triumphant mood. + STYLE
```
12. **Финал:**
```
MISSED back in the dark room, silent, a faint satisfied smile, the phone buzzes again with a new
message "Missed, there's another one...", he silently rolls his eyes. + STYLE
```

### Готовые промпты начала (копировать целиком, прикладывать `refs/missed_sheet.png`)

Текст сообщений на экране телефона не генерируем: русские буквы ИИ путает. Экран с сообщениями
делаем в монтаже поверх кадра.

**Кадр 1. Берёт телефон**
```
Use the attached character sheet as the exact reference for the character Missed: a cartoon alien mascot with a bald egg-shaped pale peach-pink head, huge glossy black eyes, long ears sticking out sideways, small sly closed-mouth smile, black oversized hoodie, black cargo pants, white sneakers. A dark bedroom at night, Missed sits alone on a couch, a phone on the low table in front of him buzzes and lights up the room with a cold blue glow, notification light flashing. He slowly reaches for it with one hand, calm and silent, mouth closed. Medium shot, the only light comes from the phone screen, deep shadows. 90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Кадр 2. Читает**
```
Use the attached character sheet as the exact reference for the character Missed: a cartoon alien mascot with a bald egg-shaped pale peach-pink head, huge glossy black eyes, long ears sticking out sideways, black oversized hoodie. Close-up from slightly below: Missed holds a phone in front of his face in a dark room, his face lit only by the cold blue screen light, the glowing screen faces away from the camera. In his huge glossy black eyes we see tiny reflections of many notification bubbles. Calm, silent, mouth closed, heavy ink shadows across his face. 90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Кадр 3. Молчаливый взгляд**
```
Use the attached character sheet as the exact reference for the character Missed: a cartoon alien mascot with a bald egg-shaped pale peach-pink head, huge glossy black eyes, long ears sticking out sideways, black oversized hoodie. Extreme close-up of Missed's face in a dark room, lit from below by a phone screen. His black eyes slowly narrow into a cold, focused stare, mouth closed, no words. Black ink shadows fall over the upper half of his face, and a faint white-blue aura starts to flicker around the tips of his ears, tiny sparks in the air. Tense, silent, the calm before the storm. 90s fighting-manga anime style, bold black ink hatching, dramatic chiaroscuro lighting, high contrast, highly detailed, vertical 9:16.
```

**Кадр 4. Втягивание (страница из 3 панелей)** — приложить `refs/missed_sheet.png`
```
Use the attached character sheet as the exact reference for the character Missed: a cartoon alien mascot with a bald egg-shaped pale peach-pink head, huge glossy black eyes, long ears sticking out sideways, black oversized hoodie, black cargo pants, white sneakers. A manga page with three dynamic diagonal panels separated by black gutters. Panel 1: close-up of a phone in Missed's hand, the glowing screen cracks like glass, light bursts through the cracks. Panel 2: Missed's hand and sleeve dissolving into glowing blue pixels and tiny chat bubbles. Panel 3: Missed's whole body pulled headfirst into a swirling vortex of light, pixels and chat bubbles, calm face, eyes open, mouth closed, motion blur and speed lines. Full-color manga style, like a colored manga page brought to life: bold black ink outlines, ink hatching and screentone dot shading, vivid colors, dramatic lighting, high contrast, speed lines, highly detailed, vertical 9:16.
```

**Кадр 5. Приземление на арену** — приложить `refs/missed_sheet.png`, `refs/fakes/sheet_05.jpg`, `refs/fakes/sheet_07.jpg`
```
Use the attached character sheet as the exact reference for the character Missed: a cartoon alien mascot with a bald egg-shaped pale peach-pink head, huge glossy black eyes, long ears sticking out sideways, black oversized hoodie, black cargo pants, white sneakers. The other attached images show fake copies of Missed with different bright skin colors and outfits. Extreme wide shot from high above: Missed lands on one knee in the center of a gigantic underground fighting arena, the floor made of giant chat message bubbles cracks in a crater around him, dust rings burst outward. Hundreds of colorful fake copies (like the attached ones: red cap, neon hoodie, hard hat with wrench, superhero cape, varsity jacket and many others) surround him in a huge circle, laughing, pointing and mocking him. Notification icons hang above like stadium spotlights, dark stands full of spectators, spam messages falling like ash. Missed is a tiny calm figure in the center, the only one in a black hoodie. Full-color manga style, like a colored manga page brought to life: bold black ink outlines, ink hatching and screentone dot shading, vivid colors, dramatic lighting, high contrast, speed lines, highly detailed, vertical 9:16.
```

**Кадр 6. Фейки смеются (страница из 3 панелей)** — приложить `refs/fakes/sheet_01.jpg`, `refs/fakes/sheet_05.jpg`, `refs/fakes/sheet_07.jpg`
```
Use the attached images as references for fake copies of the cartoon alien mascot Missed (bald egg-shaped heads, huge black eyes, long ears sticking out sideways, each with his own bright skin color and outfit). A manga page with three horizontal panels separated by black gutters, close-ups of three different fakes laughing hysterically at someone off-screen. Panel 1: the light blue pixelated fake in a green tracksuit, giggling behind his hand, glitch artifacts. Panel 2: the turquoise fake in a red cap "Mlssed", head thrown back in loud laughter, tears in his eyes. Panel 3: the green fake in a hard hat, bent over laughing and pointing with his huge wrench. Distorted fisheye angles, mocking grins, sweat drops, dark arena background with spotlights. Full-color manga style, like a colored manga page brought to life: bold black ink outlines, ink hatching and screentone dot shading, vivid colors, dramatic lighting, high contrast, speed lines, highly detailed, vertical 9:16.
```

---

## 6. 3D-сцены (Gemini / Veo, видео)

Прикладывайте лист персонажа и кадр босса. Длина каждой сцены 5–8 секунд, потом режем под бит.

1. **Приземление и облёт:**
```
Cinematic 3D: MISSED falls from a glowing pixel portal in the sky and lands on one knee in the
center of a gigantic ARENA, the floor cracks, dust rises. He slowly stands up, silent. The camera
orbits 360 degrees around him: hundreds of fake clones encircle him, laughing, giggling and pointing.
Spotlights sweep, spam ash falling. + STYLE 3D
Audio: heavy landing impact, then a chorus of mocking laughter and giggles from the clones,
crowd murmur, no music, MISSED makes no sound.
```
1а. **Фейки бросаются:**
```
Cinematic 3D: the laughter stops abruptly, all the fake clones charge at MISSED at once from every
side, he stands still, then a single blur-fast strike sends a shockwave that throws them all back,
slow motion at the moment of impact. + STYLE 3D
Audio: battle cries without words, running footsteps, a deep whoosh, a massive impact boom,
MISSED makes no sound.
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

## 7. Оживление кадров («живой комикс», как в примере автора)

Пример автора (2026-11-23): цветные комикс-кадры, каждый держится 3–5 секунд, жёсткие склейки.
Внутри кадра почти всё неподвижно, движение маленькое: чуть поворачивается голова, щурятся глаза,
дышит тело, медленный наезд камеры. В экшен-кадрах одно короткое резкое движение и снова пауза.

**Спокойные кадры:**
```
Animate this colored comic panel with subtle, minimal motion, like a living comic: the character stays almost still, only a slight head tilt, eyes slowly narrowing, gentle breathing, [действие]. Very slow camera push-in. Keep the drawing, ink lines, hatching and colors exactly as they are, no morphing, no extra movement.
```
Действия: «aura flickers at the tips of the ears», «phone light flickers on the face»,
«spam messages slowly fall in the background», «the crowd sways in the stands».

**Экшен-кадры:**
```
Animate this colored comic panel: one short, sharp, powerful motion — [действие] — then the pose freezes. Short camera shake on impact, a quick snap zoom. Keep the drawing, ink lines, hatching and colors exactly as they are, faces and proportions unchanged, no morphing.
```
Действия: «a fast sword slash and the clones burst apart», «a lightning strike from the skull»,
«the giant fist slams down», «the golden fist punches forward».

Страницы с панелями режем в монтаже на отдельные кадры и оживляем каждую панель отдельно.

## Звук

Музыка главная, звуки лежат под ней и подчёркивают удары.

- **Мисед молчит.** Никаких реплик, криков и вздохов вслух. От него слышны только удары, свист
  оружия и гул ауры.
- **Сообщения в начале:** вибрация телефона и звук уведомлений, на каждое сообщение свой.
- **Приземление на арену:** глухой тяжёлый удар и треск пола.
- **Фейки:**
  - разные смешки: хихиканье, гогот, писклявое «хи-хи», злорадное «хе-хе»;
  - насмешливый гул толпы;
  - когда бросаются в атаку, боевые выкрики без слов и топот;
  - побеждённые фейки взвизгивают и рассыпаются со звуком глитча.
- **Оружие:**
  - световой меч гудит и свистит при взмахе;
  - гипноспираль звучит «вязко», с эхом;
  - череп бьёт треском молний;
  - кукла вуду — укол иглы и стон босса;
  - золотая рука — металлический звон и самый мощный удар в ролике.
- **Босс:** низкий рёв, тяжёлые шаги, от которых трясётся камера.
- **Финальный удар:** перед ним полная тишина на один удар музыки, потом взрыв.

**Где взять звуки:**
- Gemini/Veo генерирует звук вместе с видео. Для этого в 3D-промптах есть строка `Audio:`.
- В нашем паке есть свисты, удары, глитчи и нарастания.
- Смеха и выкриков в паке нет. Их можно сгенерировать в Fish Audio (платно, сначала покажу цену)
  или взять из звука, который сгенерирует Veo.

## Монтаж

- Импакт-кадр (1–2 кадра, инверсия в чёрно-белое) на каждый сильный удар музыки.
- В затишьях медленные проезды камеры, в дропах смена кадра на каждый удар.
- Пятерых-шестерых двойников подаём стоп-кадром с надписью «Фейк №…», остальных мелькаем пачкой.
- Последняя надпись: «Настоящий Мисед ничего не просит».
