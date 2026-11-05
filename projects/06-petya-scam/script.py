"""06-petya-scam «Петя и NFT», часть 1. Four Fish Audio voices, model drama-3 (author's choice, 2026-11-05).

LINES: (speaker, spoken text, screen key, pause after, s). Speakers: N — narrator, P — Petya, K — Katya, D — Dima,
X — the sender of the last message. L28 reuses the L01 take (the same message, heard twice).
TTS_TEXT: the text sent to drama-3 — free-text directions in [brackets], NFT / RubUp spelled for Russian speech.
"""

MODEL = 'drama-3'
VOICES = {
    'N': 'af5a794626ce47988446235baed3b0af',   # narrator «russ»
    'P': '24393c0dd8f94caf96dd557cb5bbbfdb',   # Petya «Мой г»
    'K': '4c774871d6524aa6b91f98612284daa0',   # Katya «Рената Литвинова»
    'X': 'cc1b79b1108f4ed3b8aac118ba6ebd07',   # the last message «Мориарти»
    'D': '63b716a873be41e297455fced50f5f3d',   # Dima «Агрессивный школьник» (author, 2026-11-05)
}

LINES = [
    ('X', 'Зря ты это сделал, Петя.', 'hook_msg', 0.25),
    ('N', 'Петя думал, что его не вычислят. Но обо всём по порядку.', 'hook', 0.55),
    ('N', 'Однажды интернет-друг скинул ему схему.', 'boss', 1.3),
    ('P', 'Скинь календарь на пять минут? Скрин сделаю — и сразу верну.', 'ask', 0.3),
    ('D', 'Ну ладно… только правда верни.', 'dima_ok', 0.6),
    ('P', 'Спасибо, лошара.', 'loser', 0.15),
    ('D', 'Эй! Верни календарь! Я тебя найду, тебе конец!', 'threat', 0.3),
    ('P', 'Неужели… всё настолько просто?', 'simple', 0.2),
    ('N', 'Петя уснул с улыбкой. А ты пока испытай удачу в РубАп.', 'sleep', 0.3),
    ('N', 'Самый крупный улов — Катя. Богатая, и ничего не смыслит в NFT.', 'katya', 0.15),
    ('N', 'Три недели Петя искал о ней хоть что-то…', 'search', 0.1),
    ('P', 'Вот оно!', 'found', 0.15),
    ('N', 'Анкета на сайте знакомств — и парень её мечты.', 'profile', 0.15),
    ('N', 'Петя собрал его в нейросети. Александр. И написал Кате.', 'alex', 0.3),
    ('K', 'С радостью! Жду не дождусь субботы.', 'date', 0.2),
    ('P', 'Кать, прости… я не смогу приехать на свидание.', 'cancel', 0.25),
    ('K', 'Что случилось? Мы же договорились!', 'why', 0.25),
    ('P', 'Начальник подставил… скрываюсь от полиции. Буду жить на улице.', 'lie', 0.2),
    ('P', 'Какой же я гений.', 'genius', 0.25),
    ('K', 'Чего же ты молчал?! Сейчас помогу!', 'help', 1.7),
    ('K', 'Вот, держи. Это всё, что у меня было.', 'all', 0.25),
    ('N', 'Петя расплылся в улыбке. А ты пока загляни в РубАп.', 'smile', 0.2),
    ('P', 'Какая же ты наивная! Александра не существует. Прощай!', 'mock', 0.3),
    ('N', 'Петя ждал реакции. Пять минут… десять… Катя молчала.', 'wait', 0.2),
    ('N', 'Это его немного насторожило. Совсем немного.', 'uneasy', 0.3),
    ('P', 'Всё за мой счёт!', 'party', 0.3),
    ('N', 'И тут пришло одно сообщение.', 'incoming', 0.3),
    ('X', 'Зря ты это сделал, Петя.', 'final', 0.35),
    ('N', 'Как Петю могли вычислить? Продолжение — во второй части.', 'outro', 0.0),
]

TTS_TEXT = [
    '[cold, slow, menacing, quiet] Зря ты это сделал, Петя.',
    '[intriguing, brisk hooking storyteller] Петя думал, что его не вычислят. [knowing, slightly ominous] Но обо всём по порядку.',
    '[fast, mysterious] Однажды интернет-друг скинул ему схему.',
    '[friendly, sweet, persuasive, quick casual teen] Скинь календарь на пять минут? Скрин сделаю — и сразу верну.',
    '[shy, hesitant, a little unsure kid] Ну ладно… только правда верни.',
    '[smug, mocking, laughing] Спасибо, лошара.',
    '[angry, loud, quick, offended kid] Эй! Верни календарь! [threatening] Я тебя найду, тебе конец!',
    '[quiet, amazed, to himself] Неужели… [disbelieving smile] всё настолько просто?',
    '[warm, soft, slightly ironic] Петя уснул с улыбкой. [friendly, quick] А ты пока испытай удачу в РубАп.',
    '[intriguing, brisk] Самый крупный улов — Катя. Богатая, и ничего не смыслит в эн-эф-ти.',
    '[tired, slow, suspense] Три недели Петя искал о ней хоть что-то…',
    '[sudden excited shout] Вот оно!',
    '[quick, revealing] Анкета на сайте знакомств — и парень её мечты.',
    '[cool, brisk, almost admiring] Петя собрал его в нейросети. Александр. [quieter] И написал Кате.',
    '[happy, tender, in love, smiling] С радостью! Жду не дождусь субботы.',
    '[fake sad, guilty, soft] Кать, прости… я не смогу приехать на свидание.',
    '[worried, upset, quick] Что случилось? Мы же договорились!',
    '[fake despair, theatrical, pitiful] Начальник подставил… скрываюсь от полиции. Буду жить на улице.',
    '[whispering, smug grin] Какой же я гений.',
    '[caring, worried, eager to help] Чего же ты молчал?! Сейчас помогу!',
    '[gentle, sincere, a little sad] Вот, держи. Это всё, что у меня было.',
    '[sly] Петя расплылся в улыбке. [friendly, quick] А ты пока загляни в РубАп.',
    '[mocking, cruel, laughing] Какая же ты наивная! Александра не существует. Прощай!',
    '[slow, tense, suspense] Петя ждал реакции. Пять минут… десять… [quiet] Катя молчала.',
    '[quiet, ominous, slight irony] Это его немного насторожило. [pause] Совсем немного.',
    '[loud, happy, showing off, party] Всё за мой счёт!',
    '[sudden, tense, dramatic] И тут пришло одно сообщение.',
    None,
    '[intriguing, dramatic, cliffhanger] Как Петю могли вычислить? [teasing] Продолжение — во второй части.',
]
assert len(TTS_TEXT) == len(LINES)
REUSE = {28: 1}                                       # the last message reuses the take of line 1 (1-based)
