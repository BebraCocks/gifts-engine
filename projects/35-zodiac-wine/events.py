"""Shared content-time events (picture, SFX and music)."""
from timeline import DUR, ON, END, KEY, SIGN_IN, OUTRO, AD_STOP
from words import wt

FORECAST = [wt(f's{s + 1}', 'прогноз') - 0.1 for s in range(4)]     # «ПРОГНОЗ» pill + sparkles on the word
E = {
    'twelve': wt('hook', 'каждого'),          # ripple around the wheel, «12 ЗНАКОВ»
    'four': wt('hook', 'первая'),             # 4 chosen mugs glow, «ЧАСТЬ 1 · 4 ЗНАКА»
    'comments': wt('outro', 'пиши'),
    'part2': wt('outro', 'второй'),
    'end': DUR,
}
