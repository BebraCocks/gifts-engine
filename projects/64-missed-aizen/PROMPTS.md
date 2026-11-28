# 64 · Картинки для ChatGPT и видео Gemini (2026-11-26)

Стиль (решение автора): 2D, Айзен и окружение — чёрно-белая манга (тушь, скринтон, штриховка), без цвета.
Цветными остаются только Мисед (`refs/missed.jpg`) и NFT — они забирают внимание.
Промпты на английском. Ко всем картинкам Айзена прикладывайте первую удачную (`aizen_01`) как референс,
чтобы лицо и одежда совпадали. Формат 9:16. Готовые файлы кладите в `refs/` под указанными именами.

**STYLE** (добавлять в конец каждого промпта):
```
Black-and-white Japanese manga style, clean ink lines, halftone screentone shading, dramatic hatching, high contrast, no color at all, pure grayscale, shonen manga panel quality.
```

Описание персонажа (вставлять везде, где он есть) — **AIZEN:**
```
a tall, calm, elegant anime man in his thirties with wavy brown hair neatly combed back and one loose strand falling over his forehead, narrow rectangular glasses, gentle but superior half-smile, white sleeveless captain's haori over a black shinigami kimono (shihakushō), a katana at his waist
```

## Фоны

**bg_classroom.png** — класс
```
An empty Japanese school classroom in the evening, a large empty blackboard on the wall taking up the upper half of the frame, a teacher's desk in front of it, rows of student desks, tall windows on the right with low sunlight casting long shadows. No people, no text on the blackboard. Vertical 9:16. + STYLE
```

**bg_window.png** — окно для финала
```
View from inside a dark classroom toward a tall window, outside a huge low sun over rooftops, dramatic light rays and long shadows on the floor, empty space in the center of the frame for a standing figure. No people. Vertical 9:16. + STYLE
```

## Айзен (прозрачный фон, PNG)

**aizen_01_teach.png** — учитель у доски (сцены 1–2)
```
AIZEN stands in three-quarter view holding a long wooden pointer in one hand, pointing up and to the side, the other hand relaxed at his side. Calm superior smile, eyes behind glasses looking at the viewer. Full body. Transparent background, PNG with alpha, no shadow on the ground. + STYLE
```

**aizen_02_chalk.png** — пишет мелом (сцена 2)
```
AIZEN seen from behind in three-quarter view, writing on an unseen blackboard with a piece of chalk, his head slightly turned toward the viewer over his shoulder with a calm smile. Waist-up. Transparent background, PNG with alpha. + STYLE
```

**aizen_03_glasses.png** — поправляет очки (сцена 4)
```
Close-up of AIZEN's face, he slowly pushes his glasses up with one finger, a bright white glint covers the lenses and hides his eyes, faint calm smile, completely composed. Transparent background, PNG with alpha. + STYLE
```

**aizen_04_calm.png** — спокоен среди обломков лестницы (сцена 3)
```
AIZEN stands perfectly still and upright, hands hidden in the sleeves of his haori, eyes closed, serene faint smile, not bothered at all. Full body, front view. Transparent background, PNG with alpha. + STYLE
```

**aizen_05_palm.png** — смотрит на подарок (сцена 5)
```
AIZEN holds one open palm up in front of his chest and looks down at it with a calm, slightly interested expression, no surprise, the palm is empty (an object will be added later above it). Waist-up. Transparent background, PNG with alpha. + STYLE
```

**aizen_06_back.png** — спиной у окна (сцена 6)
```
AIZEN seen from behind, standing and facing away, his white haori fluttering in the wind, his head turned slightly so the corner of a calm smile is visible. Full body. Transparent background, PNG with alpha. + STYLE
```

## Плашки чата (прозрачный фон, текст ставим кодом)

**bubble_aizen.png**
```
A single empty manga-style speech bubble shaped like a messenger chat bubble with a small tail at the bottom left, white fill, bold black ink outline, subtle screentone shadow. No text inside. Wide horizontal format. Transparent background, PNG with alpha. + STYLE
```

**bubble_missed.png** — единственная цветная плашка
```
A single empty messenger chat bubble with a small tail at the bottom right, soft glossy pastel pink-peach fill with a gentle glow, thin dark outline, clean modern look. No text inside. Wide horizontal format. Transparent background, PNG with alpha.
```

## Видео Gemini (по желанию)

**aizen_06_back → короткая петля 4 с** (финал): приложить `aizen_06_back.png` на сером фоне.
```
Animate this black-and-white manga illustration. The man stands still facing away, only his white haori and hair flutter slowly in the wind, the corner of his smile slightly widens at the end. Static camera, keep the manga ink and screentone style, no color. 4 seconds. No sound.
```

Остальное (лестница мелом, обрушение, волны, вылет подарка, пульс Миседа) — кодом.
