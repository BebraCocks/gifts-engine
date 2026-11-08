"""Shared content-time events (picture, SFX and music)."""
from timeline import DUR, ON, END, KEY, SIGN_IN, OUTRO, AD_STOP
from words import wt

# the forecast sentence starts (v3: no word «прогноз», author): sparkles fly out, stars flash
FORECAST = [wt(f's{s + 1}', w) - 0.1 for s, w in enumerate(('начинай', 'не', 'скажи', 'позвони'))]
E = {
    'twelve': wt('hook', 'ещё'),          # ripple around the wheel, «12 ЗНАКОВ»
    'four': wt('hook', 'четыре'),             # 4 chosen mugs glow, «ЧАСТЬ 1 · 4 ЗНАКА»
    'comments': wt('outro', 'пиши'),
    'end': DUR,
}
