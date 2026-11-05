"""04-calendar-craft «Первый крафт». Speakers: N = narrator (author's voice), A = Алексей, M = Михаил.
LINES: (speaker, spoken text, screen key, pause after, s). The pause holds silent action beats
(the burn, the throw, the legendary reveal, the shocked stare) — see STORYBOARD.md section 3.
TTS: the same words with Fish Audio drama-3 directions in [brackets] (English) and word tags."""

VOICES = {
    'N': '7312c38557eb4fb384e3874e8e9cea67',   # narrator, author's default
    'A': 'ce15cf1a0cc74f66a5da17bdc2f79e6a',   # Алексей
    'M': 'b517ea6004bb4861863747c1d837a307',   # Михаил
}
MODEL = 'drama-3'

LINES = [
    ('N', 'Три года без обедов — ради одной кнопки.', 'hook', 0.25),
    ('N', 'Алексей копил на крафт: худел, бледнел… но накопил.', 'saving', 0.2),
    ('N', 'Пятьдесят семь календарей — только из крафта. Легендарных — пять.', 'vault3d', 0.2),
    ('A', 'Наконец-то, сука! Мой первый крафт!', 'first', 0.8),
    ('A', 'Ну… с богом.', 'press', 1.9),
    ('N', 'Горящее время, Разбитое сердце… Названия, блядь, намекали.', 'burned', 0.15),
    ('A', 'Восемьдесят девять процентов?! Вы там охуели?!', 'rage', 0.65),
    ('N', 'Стоп-кадр. Пока он ищет новый телефон — испытай удачу в РубАп.', 'ad', 0.3),
    ('M', 'Что случилось?', 'misha', 0.15),
    ('A', 'Крафт… восемьдесят девять процентов… всё сгорело нахуй.', 'tells', 0.2),
    ('M', 'О, у меня тоже один есть. Сейчас попробую.', 'try', 0.55),
    ('M', 'Двадцать два процента? Да похуй, жму.', 'one', 2.1),
    ('M', 'Фу, хуйня какая-то некрасивая. О, предлагают сто рублей!', 'ugly', 0.35),
    ('M', 'Отлично! Пойду куплю пиццу в столовой. Удачно я продал!', 'pizza', 0.45),
    ('A', 'Ты чё, ебанутый?!', 'wtf', 0.3),
    ('N', 'Мораль: проценты не знают, сколько обедов ты пропустил.', 'moral', 0.25),
    ('N', 'Ставь лайк, если у тебя тоже есть друг-долбаёб.', 'cta', 0.0),
]

# The words actually sent to Fish Audio drama-3 (chosen takes in takes.json). Directions in [brackets].
TTS_TEXT = [
    '[fast-paced punchy hook, intriguing] Три года без обедов — ради <emphasis>одной кнопки</emphasis>.',
    '[quick, ironic storyteller] Алексей копил на крафт: худел, бледнел… но накопил.',
    '[brisk, engaging] Пятьдесят семь календарей — <emphasis>только из крафта</emphasis>. '
    'Легендарных — <emphasis>пять</emphasis>.',
    '[overjoyed, almost crying from happiness] Наконец-то, сука! Мой <emphasis>первый</emphasis> крафт!',
    '[nervous whisper, holding breath] Ну… с богом.',
    '[brisk, dry humor] Горящее время, Разбитое сердце… Названия, блядь, намекали.',
    '[furious, screaming, losing his mind] Восемьдесят девять процентов?! Вы там <forceful>охуели</forceful>?!',
    '[quick, friendly, a sly wink] Стоп-кадр. Пока он ищет новый телефон — испытай удачу в РубАп.',
    '[casual, relaxed, mouth full] Что случилось?',
    '[sobbing, fast] Крафт… восемьдесят девять процентов… всё сгорело <emphasis>нахуй</emphasis>.',
    '[carefree, cheerful, quick] О, у меня тоже один есть. Сейчас попробую.',
    '[careless, lazy, chewing] Двадцать два процента? Да похуй, жму.',
    '[disgusted, bored] Фу, хуйня какая-то некрасивая. [pleased, quick] О, предлагают сто рублей!',
    '[happy, carefree, quick] Отлично! Пойду куплю пиццу в столовой. Удачно я продал!',
    '[shocked, disbelief, shouting] Ты чё, <forceful>ебанутый</forceful>?!',
    '[wise, warm, slightly ironic] Мораль: проценты не знают, сколько обедов ты пропустил.',
    '[energetic, playful, laughing] Ставь лайк, если у тебя тоже есть друг-долбаёб.',
]
assert len(TTS_TEXT) == len(LINES)
