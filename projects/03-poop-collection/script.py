"""(spoken narration, on-screen key, style, pause after). Soft wording; Latin names spelled for the voice.
Natural speaking speed (Fish Audio drama-3, no speed-up): the text is short enough to fit 58–59 s."""
LINES = [
    ('Какашки по цене золота? Такая банка правда есть в Телеграме.', 'hook', 'hook', 0.15),
    ('Жук-навозник — первое животное, которое находит дорогу по Млечному Пути.', 'Dung Beetle', 'hero', 0.35),
    ('Копи лювак: кофе, прошедший через циветту, — до тысячи трёхсот долларов за кило.', 'Shitty Coffee', 'hero', 0.2),
    ('Скибиди Туалет — редкость одна десятая процента. Мем вырос из ролика в одиннадцать секунд.',
     'Skibidi Toilet', 'hero', 0.2),
    ('А дальше — два шедевра.', 'teaser', 'teaser', 0.4),
    ('Банан Каттелана на скотче: его купили за шесть миллионов долларов… и съели.', 'Modern Art', 'hero', 0.3),
    ('А вот и банка Пьеро Мандзони: тридцать грамм по цене золота. Одну продали за двести семьдесят пять тысяч евро.',
     'Art Supplies', 'hero', 0.2),
    ('Подаренная какашка — не обида, а искусство. Перешли тому, кто не понял.', 'final', 'final', 0.0),
]

# Directed text for Fish Audio drama-3: plain-language directions in [brackets] (English), word tags.
# Spoken words are identical to LINES[k][0]; timing and captions use LINES.
TTS_TEXT = [
    '[punchy, energetic hook, a sly smile] Какашки <emphasis>по цене золота</emphasis>? Такая банка правда есть в Телеграме.',
    '[enthusiastic science storyteller] Жук-навозник — первое животное, которое находит дорогу '
    '<emphasis>по Млечному Пути</emphasis>.',
    '[playful surprise] Копи лювак: кофе, прошедший через циветту, — <emphasis>до тысячи трёхсот долларов</emphasis> за кило.',
    '[upbeat] Скибиди Туалет — редкость <emphasis>одна десятая процента</emphasis>. '
    '[amused] Мем вырос из ролика в одиннадцать секунд.',
    '[mysterious, slightly lower voice] А дальше — два <emphasis>шедевра</emphasis>.',
    '[ironic] Банан Каттелана на скотче: его купили за <emphasis>шесть миллионов долларов</emphasis>… и съели.',
    '[impressed, warm] А вот и банка Пьеро Мандзони: тридцать грамм по цене золота. '
    'Одну продали за <emphasis>двести семьдесят пять тысяч евро</emphasis>.',
    '[warm, smiling] Подаренная какашка — не обида, а <emphasis>искусство</emphasis>. '
    'Перешли тому, кто не понял.',
]
