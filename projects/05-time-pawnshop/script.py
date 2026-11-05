"""05-time-pawnshop «Ломбард времени». One voice (author's default narrator); the watchmaker's lines (W)
are read by the same voice with an «old, slow, low» direction.
LINES: (speaker, spoken text, screen key, pause after, s). Pauses hold silent beats (see STORYBOARD.md §3).
TTS_TEXT: the words actually sent to Fish Audio drama-3 — directions in [brackets], gift names transliterated
so the Russian voice says them cleanly."""

VOICE = '7312c38557eb4fb384e3874e8e9cea67'
MODEL = 'drama-3'

LINES = [
    ('N', 'За этого Пепе он отдал вечер с бабушкой.', 'hook', 0.25),
    ('N', 'Бабушка звала Лёву в субботу на пирог.', 'invite', 0.12),
    ('N', 'Ночью написал бот: «Ломбард времени. Покупаем часы жизни за подарки».', 'bot', 0.2),
    ('N', 'Час в очереди — Ginger Cookie. Проспанное воскресенье — Snow Globe.', 'cheap', 0.15),
    ('N', 'Но ломбард платил честно: чем дороже час для тебя — тем дороже подарок.', 'rule', 0.15),
    ('N', 'Лето с друзьями — Record Player. Пропущенная поездка — Durov\'s Cap.', 'rich', 0.2),
    ('N', 'А потом часовщик достал главный лот…', 'safe', 0.45),
    ('N', 'Plush Pepe. Цена — одна суббота. Та самая.', 'lot', 0.15),
    ('N', '«Съезжу в другой раз», — подумал Лёва. И подписал.', 'sign', 0.3),
    ('N', 'Другого раза не случилось.', 'never', 0.85),
    ('N', 'Лёва принёс назад всю коллекцию: «Верните субботу».', 'return', 0.2),
    ('W', 'Обратно не продаю. Дороже всего — то, что нельзя вернуть.', 'refuse', 0.3),
    ('W', 'А ты? Plush Pepe — за вечер с тем, кто тебя ждёт?', 'you', 0.25),
    ('N', 'Пиши в комментах: лягушка или часы?', 'vote', 0.0),
]

TTS_TEXT = [
    '[fast, punchy, intriguing hook] За этого Пепе он отдал вечер с бабушкой.',
    '[warm, gentle storyteller] Бабушка звала Лёву в субботу на пирог.',
    '[rapid, mysterious] Ночью написал бот: [quick, eerie] Ломбард времени. Покупаем часы жизни за подарки.',
    '[rapid, amused] Час в очереди — Джинджер Куки. Проспанное воскресенье — Сноу Глоуб.',
    '[brisk, serious, meaningful] Но ломбард платил честно: чем дороже час <emphasis>для тебя</emphasis> — '
    'тем дороже подарок.',
    '[rapid, building tension] Лето с друзьями — Рекорд Плеер. Пропущенная поездка — Дуровс Кэп.',
    '[hushed, quick, suspenseful] А потом часовщик достал главный лот…',
    '[awed] Плюш Пепе. [quiet, heavy] Цена — одна суббота. Та самая.',
    '[careless, casual] Съезжу в другой раз, — [narrator, flat] подумал Лёва. И подписал.',
    '[very quiet, sad, slow] Другого раза не случилось.',
    '[desperate, urgent] Лёва принёс назад всю коллекцию: [pleading] Верните субботу.',
    '[old man, calm, wise, brisk] Обратно не продаю. Дороже всего — то, что <emphasis>нельзя вернуть</emphasis>.',
    '[old man, sly challenge, quick] А ты? Плюш Пепе — за вечер с тем, кто тебя ждёт?',
    '[friendly, quick, inviting] Пиши в комментах: лягушка или часы?',
]
assert len(TTS_TEXT) == len(LINES)
