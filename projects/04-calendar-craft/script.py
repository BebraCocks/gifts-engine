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
    ('A', 'Наконец-то! Мой первый крафт!', 'first', 0.6),
    ('A', 'Восемьдесят девять процентов… Ну, с богом.', 'press', 2.4),
    ('N', 'Горящее время, Разбитое сердце… Названия намекали.', 'burned', 0.2),
    ('A', 'Восемьдесят девять процентов?! Издеваетесь?!', 'rage', 0.9),
    ('N', 'Стоп-кадр. Пока он ищет новый телефон — испытай удачу в РубАп.', 'ad', 0.4),
    ('M', 'Что случилось?', 'misha', 0.15),
    ('A', 'Крафт… восемьдесят девять процентов… всё сгорело.', 'tells', 0.2),
    ('M', 'О, у меня тоже один есть. Сейчас попробую.', 'try', 0.2),
    ('N', 'Один календарь. Шанс — двадцать два процента.', 'one', 2.5),
    ('M', 'Фу, какая-то некрасивая. О, предлагают сто рублей.', 'ugly', 0.35),
    ('M', 'Отлично! Пойду куплю пиццу в столовой. Удачно я продал!', 'pizza', 1.0),
    ('N', 'Мораль: проценты не знают, сколько обедов ты пропустил.', 'moral', 0.25),
    ('N', 'Ставь лайк, если у тебя тоже есть друг-долбаёб.', 'cta', 0.0),
]

# The words actually sent to Fish Audio drama-3 (chosen takes in takes.json). Directions in [brackets].
TTS_TEXT = [
    '[fast-paced punchy hook, intriguing] Три года без обедов — ради <emphasis>одной кнопки</emphasis>.',
    '[quick, ironic storyteller] Алексей копил на крафт: худел, бледнел… но накопил.',
    '[brisk, engaging] Пятьдесят семь календарей — <emphasis>только из крафта</emphasis>. '
    'Легендарных — <emphasis>пять</emphasis>.',
    '[overjoyed, voice trembling with happiness] Наконец-то! Мой <emphasis>первый</emphasis> крафт!',
    '[nervous, excited whisper, holding breath] Восемьдесят девять процентов… Ну, с богом.',
    '[deadpan, dry humor, brisk] Горящее время, Разбитое сердце… Названия намекали.',
    '[furious, screaming, losing it] Восемьдесят девять процентов?! <forceful>Издеваетесь</forceful>?!',
    '[quick, friendly, a sly wink] Стоп-кадр. Пока он ищет новый телефон — испытай удачу в РубАп.',
    '[casual, relaxed, mouth full] Что случилось?',
    '[devastated, broken voice, almost crying] Крафт… восемьдесят девять процентов… всё сгорело.',
    '[carefree, cheerful, quick] О, у меня тоже один есть. Сейчас попробую.',
    '[tense whisper, quick] Один календарь. Шанс — двадцать два процента.',
    '[disgusted, bored] Фу, какая-то некрасивая. [pleased, quick] О, предлагают сто рублей.',
    '[happy, carefree, quick] Отлично! Пойду куплю пиццу в столовой. Удачно я продал!',
    '[wise, warm, slightly ironic] Мораль: проценты не знают, сколько обедов ты пропустил.',
    '[energetic, playful, laughing] Ставь лайк, если у тебя тоже есть друг-долбаёб.',
]
assert len(TTS_TEXT) == len(LINES)
