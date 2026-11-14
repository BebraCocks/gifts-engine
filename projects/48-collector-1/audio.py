"""«Коллекционер», часть 1 — полный звук: голоса (voice/LNN.wav, prep_voice.py) + SFX (Botanica V4 через sfxkit,
бесплатная библиотека Fish в input/ext/, недостающее — synth.py) + две вставки RubUp с полным звуком.
Пишет build/mix.wav, build/timeline.json и для автора build/review/{mix,sfx_only,voice_only}.mp3 + sfx_cues.txt.
Время в коде — время содержания (до вставок рекламы)."""
import json
import subprocess
import sys
import wave
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
sys.path.insert(0, str(HERE))
import numpy as np
import banner
import sound
import sfxkit
import synth
import script

SR = 48000
META = json.loads((HERE / 'voice' / 'lines.json').read_text(encoding='utf-8'))
LEAD = 0.25
# пауза после реплики (с): место для звуков действия; RubUp — после реплик script.AD_AFTER
PAUSE = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.3, 5: 0.1, 6: 0.05, 7: 0.1, 8: 0.5, 9: 0.35, 10: 0.3, 11: 0.7,
         12: 0.25, 13: 0.2, 14: 0.2, 15: 0.45, 16: 0.65, 17: 0.15, 18: 0.5,
         19: 0.75, 20: 0.15, 21: 0.35, 22: 0.85, 23: 0.4, 24: 0.8}
FX_DB, BED_DB = 8.0, 5.0      # общий уровень звуков и фона относительно голоса
AD_GAP = 0.25          # после остановки на рекламу речь продолжается через столько секунд


def timeline():
    on, stops = {}, []
    t = LEAD
    for m in META:
        i = m['line']
        on[i] = t
        t += m['dur'] + PAUSE[i]
        if i in script.AD_AFTER:
            stop = t - PAUSE[i] / 2
            stops.append(round(stop, 3))
            t = stop + AD_GAP + 0.05
    return on, stops, t


ON, STOPS, DUR = timeline()
END = {m['line']: ON[m['line']] + m['dur'] for m in META}
GAPS = {m['line']: m['gaps'] for m in META}
BR = banner.Breaks(STOPS, cy=960, speed=1.1)


def g(i, k):
    """Время k-й паузы внутри реплики i."""
    return ON[i] + GAPS[i][k]


def place(buf, x, t, gain_db, cues=None, label='', pan=None):
    i0 = int(round(t * SR))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if pan is not None:
        l, r = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2), np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
        x = x * np.array([min(1, l), min(1, r)])
    n = min(len(x), len(buf) - i0)
    if n > 0:
        buf[i0:i0 + n] += x[:n] * 10 ** (gain_db / 20)
    if cues is not None:
        cues.append(dict(t=round(t, 3), at=round(t, 3), align='start', gain_db=gain_db, pan=pan or 0, label=label,
                         role='synth', id='synth.py', peak=0.0))


def ext(name, seg=None, hp=None):
    x = sound.load_stereo(HERE / 'input' / 'ext' / name, SR)
    if seg:
        x = x[int(seg[0] * SR):int(seg[1] * SR)].copy()
        f = min(len(x) // 4, int(0.02 * SR))
        x[:f] *= np.linspace(0, 1, f)[:, None]
        x[-f:] *= np.linspace(1, 0, f)[:, None]
    if hp:
        x = np.stack([synth.highpass(x[:, c], hp) for c in range(2)], 1)
    return x / (np.abs(x).max() + 1e-9)


def ext_add(buf, cues, name, t, gain_db, label, seg=None, hp=None, pan=None):
    place(buf, ext(name, seg, hp), t, gain_db, None, pan=pan)
    cues.append(dict(t=round(t, 3), at=round(t, 3), align='start', gain_db=gain_db, pan=pan or 0, label=label,
                     role='ext', id=f'input/ext/{name}', peak=0.0))


def voice_layer(n):
    v = np.zeros((n, 2))
    for m in META:
        i = m['line']
        with wave.open(str(HERE / 'voice' / f'L{i:02d}.wav')) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32768
        place(v, x, ON[i], 0.0)
    return v


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    bed = np.zeros((n, 2))             # фон: тишина комнаты и гул (не уходит в sfx-реплики cues)
    C = kit.cues
    add = kit.add
    # ---------------- фон: ночная тишина однушки весь ролик; гул страха — с условия и с прихода «мамы»
    place(bed, synth.roomtone(DUR + 1, 1), 0.0, -40)
    add(bed, 'ambience', 0.0, gain_db=-36, file='ambience-nature-night', vary=False, fit=DUR, fade_out=1.0,
        label='фон: ночь за окном (окраина)')
    place(bed, synth.drone(END[5] - ON[4] + 2, 3), ON[4] - 0.5, -26, C, 'гул: условие от неизвестного')
    place(bed, synth.drone(STOPS[0] - ON[9] + 0.5, 4, base=36.7), ON[9], -27, C, 'гул: стук в 01:37, до рекламы')
    place(bed, synth.drone(END[18] - ON[12] + 1, 5, base=32.7), ON[12], -24, C, 'гул: «мама» — монстр — выбивание')
    place(bed, synth.drone(DUR - ON[22] + 0.5, 6, base=36.7), ON[22] + 2.0, -28, C, 'гул: снова стук, опрос')

    # ---------------- 00:00 тикток, сообщение
    for k, dt in enumerate((0.15, 1.0, 1.9)):
        add(fx, 'whoosh-short', ON[1] + dt, gain_db=-24, pan=0.1 * (k - 1), label=f'листает тикток: свайп {k + 1}')
    add(fx, 'popup', ON[1] + 4.1, gain_db=-14, label='уведомление: сообщение от неизвестного')
    add(fx, 'typing', ON[2] - 0.1, gain_db=-24, fit=1.6, fade_out=0.3, label='текст сообщения печатается')
    add(fx, 'glitch-text', ON[2] + 3.52, gain_db=-21, label='«…одно условие» — сбой текста')
    add(fx, 'click', END[3] - 0.05, gain_db=-14, label='жмёт «Принять»')
    add(fx, 'confirm', END[3] + 0.08, gain_db=-20, label='принято')
    add(fx, 'typing', ON[4] + 1.2, gain_db=-25, fit=2.0, fade_out=0.4, label='неизвестный дописывает условие')
    add(fx, 'sub-drop', ON[4] + 4.67, gain_db=-17, label='«…охотиться Коллекционер»')
    add(fx, 'riser', END[4] - 3.0, gain_db=-24, fit=3.0, fade_out=0.1, label='напряжение к концу условия')
    # ---------------- подарок, продажа
    add(fx, 'popup', END[4] + 0.6, gain_db=-15, label='дзынь: пришёл подарок')
    add(fx, 'sparkle', END[4] + 0.8, gain_db=-18, label='Лут Бэг появляется')
    add(fx, 'granular-combo', END[4] + 0.9, gain_db=-22, fit=1.5, fade_out=0.4, label='блеск NFT')
    add(fx, 'coin', ON[6] + 0.3, gain_db=-20, label='«продаю!» — мечтает о деньгах')
    add(fx, 'click', ON[6] + 0.6, gain_db=-18, label='жмёт «Продать»')
    add(fx, 'error', ON[7] + 0.1, gain_db=-15, label='«Продажа недоступна 24 ч»')
    add(fx, 'downlifter', END[8] - 0.1, gain_db=-20, label='перебивка времени → 01:37')
    add(fx, 'glitch', END[8] + 0.45, gain_db=-21, label='таймер 01:37')
    # ---------------- 01:37 стук, «мама»
    kn = synth.knocks([0, 0.32, 0.6], 1.0, seed=11)
    place(fx, kn, ON[9] + 1.29, -12, C, 'стук в дверь ×3')
    ext_add(fx, C, 'footsteps_carpet.mp3', ON[9] + 2.33, -22, 'идёт к двери', seg=(2.0, 4.2))
    add(fx, 'impact', END[9] - 0.25, gain_db=-22, label='«…что-то его останавливает»')
    place(fx, synth.knocks([0, 0.28], 0.7, seed=21), ON[10] - 0.55, -15, C, 'снова тихий стук')
    place(fx, synth.heartbeat(5, 88), ON[11] + 1.5, -15, C, 'сердцебиение — проверка «мамы»')
    add(fx, 'riser', STOPS[0] - 1.6, gain_db=-23, fit=1.6, fade_out=0.05, label='молчание за дверью → RubUp №1')
    # ---------------- после RubUp №1: «шестого»
    add(fx, 'riser-hit', END[12] - 0.45, gain_db=-14, label='«…шестого» — удар страха')
    add(fx, 'sub-drop', END[12] - 0.4, gain_db=-17, label='«…шестого» — низ')
    add(fx, '*', ON[13] + 0.3, gain_db=-20, file='plastic-creaks-01', vary=False, label='пятится: скрип пола')
    add(fx, 'popup', ON[14] + 0.6, gain_db=-17, label='сообщение «Удачи 😇»')
    add(fx, 'glitch', ON[14] + 2.62, gain_db=-16, label='чат исчезает')
    add(fx, 'whoosh-deep', ON[15] - 0.4, gain_db=-20, label='голос монстра из-за двери')
    add(fx, 'sub-drop', ON[15] + 3.0, gain_db=-17, label='«Открой. Дверь.»')
    place(fx, synth.knocks([0, 0.9], 1.0, seed=31), END[15] + 0.05, -16, C, 'последние медленные удары')
    # ---------------- выбивание двери
    t0 = END[16] + 0.15
    hits = [0, 0.95, 1.7, 2.3, 3.4, 4.0, 4.6, 5.6, 6.2, 6.7, 7.6, 8.2, 8.7, 9.3, 9.8, 10.3]
    hits = [h for h in hits if t0 + h < STOPS[1] - 0.3]
    for k, h in enumerate(hits):
        place(fx, synth.bash(40 + k, 1.0), t0 + h, -9 - (2 if k % 3 == 1 else 0), C, f'удар в дверь {k + 1}')
        if k % 3 == 0:
            ext_add(fx, C, 'punch_heavy.mp3', t0 + h, -16, f'удар в дверь {k + 1}: тело удара')
    ext_add(fx, C, 'door_slam.mp3', t0, -10, 'первый удар: дверь содрогается')
    place(fx, synth.scrape(1.0, 7), ON[17] + 0.05, -16, C, 'тащит кровать')
    place(fx, synth.scrape(0.9, 8), ON[17] + 1.0, -17, C, 'двигает шкаф')
    add(fx, '*', ON[17] + 2.2, gain_db=-17, file='ice-cube', vary=False, label='ставит банку огурцов (стекло)')
    add(fx, '*', ON[18] + 2.2, gain_db=-14, file='demolition', vary=False, label='дверь трещит')
    add(fx, '*', ON[18] + 1.0, gain_db=-19, file='plastic-creaks-02', vary=False, label='петли скрипят')
    add(fx, 'riser', STOPS[1] - 2.0, gain_db=-20, fit=2.0, fade_out=0.05, label='«это конец» → RubUp №2')
    # ---------------- после RubUp №2: сирены, банка
    place(fx, synth.bash(90, 1.0), STOPS[1] + 0.35, -8, C, 'последний удар после рекламы')
    place(fx, synth.siren(9.0, 2), STOPS[1] + 0.4, -15, C, 'сирена за окном, подъезжает')
    ext_add(fx, C, 'explosion_glass.mp3', END[19] + 0.2, -12, 'банка огурцов разбивается (только стекло)',
            seg=(0.25, 2.6), hp=1800)
    add(fx, '*', END[19] + 0.22, gain_db=-14, file='foley/drop', vary=False, semitones=-5, label='банка падает на пол')
    add(fx, '*', END[19] + 0.45, gain_db=-24, file='ice-cube', vary=False, semitones=3, label='осколки')
    add(fx, 'downlifter', ON[21] - 0.1, gain_db=-24, label='«мои огурчики…»')
    place(fx, synth.scrape(0.8, 9), ON[22] + 0.2, -20, C, 'расставляет мебель')
    add(fx, '*', ON[22] + 1.3, gain_db=-24, file='friction', vary=False, label='вытирает пол')
    add(fx, 'glitch', ON[22] + 2.05, gain_db=-21, label='таймер 01:59')
    place(fx, synth.knocks([0, 0.25, 0.5, 0.75], 1.15, seed=51), END[22] + 0.15, -10, C, 'резкий стук: «полиция»')
    # ---------------- опрос
    add(fx, 'impact', ON[24] + 0.1, gain_db=-20, label='«до второго подарка — одна минута»')
    for s in range(10):
        add(fx, 'click', ON[24] + 0.2 + s * 1.0, gain_db=-27, key='tick', vary=False, semitones=2 * (s % 2),
            label=f'тикает таймер до подарка {s + 1}')
    for k, dt in enumerate((2.72, 3.92, 6.1)):
        add(fx, 'select', ON[24] + dt, gain_db=-17, label=f'вариант {"АБВ"[k]}')
    add(fx, 'riser-hit', END[24] - 0.2, gain_db=-17, label='финал: «пиши в комментариях»')
    return fx, bed


def limit(x, knee=0.70, ceil=0.89):
    a = np.abs(x)
    over = a > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (ceil - knee) * np.tanh((a[over] - knee) / (ceil - knee)))
    return y


def mp3(x, path):
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-b:a', '192k', str(path)], input=np.clip(x, -1, 1).astype('<f4').tobytes(), check=True)


def main():
    n = int(round(DUR * SR))
    kit = sfxkit.Kit(HERE, seed=zlib.crc32(b'48-collector-1'))
    voice = voice_layer(n)
    fx, bed = sfx_layer(n, kit)
    env = np.convolve(np.abs(voice).max(1), np.ones(2400) / 2400, 'same')
    k = np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1)
    k = np.convolve(k, np.ones(4800) / 4800, 'same')
    fx *= (1 - 0.45 * k)[:, None] * 10 ** (FX_DB / 20)      # звуки уступают голосу
    bed *= (1 - 0.3 * k)[:, None] * 10 ** (BED_DB / 20)
    gain = 10 ** (2.5 / 20)
    content = limit((voice * 1.0 + fx + bed) * gain)
    data = BR.audio(content, SR)
    b = paths.build(HERE)
    with wave.open(str(b / 'mix.wav'), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    if '--save' in sys.argv:
        kit.save(BR)
    rev = sfxkit.write_review(HERE, (fx + bed) * gain, data, BR, SR, kit.cues)
    mp3(BR.audio(voice * gain, SR, banner=False), rev / 'voice_only.mp3')
    (b / 'timeline.json').write_text(json.dumps(dict(on=ON, end=END, gaps=GAPS, stops=STOPS, dur=DUR,
                                                     out_dur=BR.out_dur(DUR)), ensure_ascii=False, indent=1))
    print(f'содержание {DUR:.1f} с, с рекламой {BR.out_dur(DUR):.1f} с; RubUp на {STOPS}')


if __name__ == '__main__':
    main()
