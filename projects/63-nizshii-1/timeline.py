"""Тайминг по реальной длине клипов voice/clips/*.wav."""
from pathlib import Path
import wave
from script import CLIPS, LEAD

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / 'clips' / f'{c[0]}.wav' for c in CLIPS]
HAS_NARRATION = all(p.is_file() for p in TAKES)
KEYS = [c[0] for c in CLIPS]
ON, END = [], []
cursor = LEAD
for k, (key, take, t0, t1, pause, caps) in enumerate(CLIPS):
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            dur = w.getnframes() / w.getframerate()
    else:
        dur = t1 - t0
    ON.append(cursor)
    END.append(cursor + dur)
    cursor += dur + pause
DUR = cursor
S = dict(zip(KEYS, ON))
E = dict(zip(KEYS, END))
# подписи в абсолютном времени: (начало, конец, текст, акцент)
CAPS = []
for k, c in enumerate(CLIPS):
    caps = c[5]
    for j, (dt, text, acc) in enumerate(caps):
        t_on = ON[k] + dt
        t_off = ON[k] + caps[j + 1][0] if j + 1 < len(caps) else END[k] + min(0.35, c[4] * 0.8)
        CAPS.append((t_on, t_off, text, acc))
# границы сцен
SC2 = S['O2'] - 0.35          # профиль без памяти
SC3 = S['Y1'] - 0.22          # крик Йорки и номер 11
STAMP = E['Y1'] + 0.12        # удар «11»

if __name__ == '__main__':
    for k in KEYS:
        print(k, round(S[k], 2), round(E[k], 2))
    print('DUR', round(DUR, 2))
